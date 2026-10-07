"""Discord slash-command shell. Run on a PC with League for live data."""

from __future__ import annotations

import asyncio
import io
import logging
import os
import queue
import subprocess
import tempfile
import time
from pathlib import Path

import discord
import edge_tts
import imageio_ffmpeg
from discord import app_commands
from discord.ext import voice_recv

import lane_playbook
from coach import (LESSON_TRIGGERS, NOTE_NOT_SAVED, Topic, active_champion, active_role, coach, evidence, explain,
                   is_noise, quick_intent, read_live_game, summarize_game)
from coordinators import CoordinatorBoard
from credentials import load_discord_token
from intent_router import IntentRouterError, route_question
from local_hotkey import HotkeyCapture, input_devices
from local_questions import answer_tools
from minimap_reader import DEFAULT_RECT, MinimapWatcher
from model_profiles import Profiles
from model_pipeline import enhance_chain, brief_for, draft
from scoreboard_reader import ScoreboardWatcher
from voice_input import WAKE, CoachSink, load_model, question_after_wake, transcribe_pcm

# Voice receive logs an RTCP line every second; keep warnings and errors only.
for _name in ("discord.ext.voice_recv.reader", "discord.ext.voice_recv.gateway"):
    logging.getLogger(_name).setLevel(logging.WARNING)

DEFAULT_QUESTION = "What are our options now?"
TOPIC_SECONDS = 180       # "explain more" works this long after the last delivered read or layer
TOPIC_MAX_SECONDS = 360   # and never longer than this after the read itself
# On /listen, a bare "stop" with no wake word silences the coach while it is speaking. A friend in the
# call can trigger it; the cost is silence. False removes it.
LISTEN_BARE_STOP = True


class CoachBot(discord.Client):
    def __init__(self) -> None:
        super().__init__(intents=discord.Intents.default())
        self.tree = app_commands.CommandTree(self)
        self.style: dict[int, str] = {}
        self.synced_guilds: set[int] = set()
        self.listen_channels: dict[int, discord.abc.Messageable] = {}
        self.listen_sinks: dict[int, CoachSink] = {}
        self.hotkeys: dict[int, HotkeyCapture] = {}
        self.hotkey_versions: dict[int, int] = {}
        self.request_versions: dict[int, int] = {}
        # The last delivered read per guild, for "explain more"; and the request version a "stop" ended.
        self.topics: dict[int, Topic] = {}
        self.topic_at: dict[int, float] = {}
        self.topic_read_at: dict[int, float] = {}
        self.stopped_versions: dict[int, int] = {}
        self.coordinators = CoordinatorBoard()
        self.coordinator_task: asyncio.Task | None = None
        self.minimap: MinimapWatcher | None = None
        self.models = Profiles()
        self.generations: dict[int, asyncio.Task] = {}
        self.scoreboard: ScoreboardWatcher | None = None

    async def setup_hook(self) -> None:
        guild_id = os.getenv("DISCORD_GUILD_ID", "").strip()
        if guild_id:
            guild = discord.Object(id=int(guild_id))
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)

    async def on_ready(self) -> None:
        if self.scoreboard is None and os.getenv("COACH_SCOREBOARD", "1") == "1":
            self.scoreboard = ScoreboardWatcher(lambda: summarize_game(read_live_game()))
            self.scoreboard.start()
            print("Scoreboard capture on: League foreground, Tab opens, local Windows OCR.", flush=True)
        if self.coordinator_task is None or self.coordinator_task.done():
            self.coordinator_task = asyncio.create_task(self.poll_coordinators())
        # Screen grabs happen only while the live feed reports a match, so this is safe to leave on.
        if self.minimap is None and os.getenv("COACH_MINIMAP", "1") == "1":
            rect = tuple(int(v) for v in os.getenv("COACH_MINIMAP_RECT", ",".join(map(str, DEFAULT_RECT))).split(","))
            self.minimap = MinimapWatcher(rect, live_teams)
            self.minimap.start()
            print(f"Minimap reader on for rect {rect}.", flush=True)
        for guild in self.guilds:
            if guild.id not in self.synced_guilds:
                self.tree.copy_global_to(guild=guild)
                await self.tree.sync(guild=guild)
                self.synced_guilds.add(guild.id)
                print(f"Commands ready in {guild.name} (ID {guild.id})", flush=True)
        for problem in lane_playbook.lesson_problems(LESSON_TRIGGERS):
            print(f"Lesson file: {problem}", flush=True)
        print(f"Bot online as {self.user}", flush=True)

    async def poll_coordinators(self) -> None:
        while not self.is_closed():
            try:
                data = await asyncio.to_thread(read_live_game)
                self.coordinators.observe(summarize_game(data))
            except (OSError, ValueError):
                pass
            except Exception as exc:
                print(f"Coordinator poll failed: {type(exc).__name__}: {exc}", flush=True)
            await asyncio.sleep(5)

    async def on_message(self, message: discord.Message) -> None:
        if message.author.bot or not self.user or self.user not in message.mentions:
            return
        question = message.content.replace(f"<@{self.user.id}>", "").replace(
            f"<@!{self.user.id}>", "").strip()
        if not question:
            await message.reply("Ask me a question after the mention, or use /ask.", mention_author=False)
            return
        if stop_asked(question):
            silence(message.guild, question)
            return
        version = begin_request(message.guild)
        async with message.channel.typing():
            answer = await make_answer(message.guild.id if message.guild else 0, question)
        if not current_request(message.guild, version) or not current_reply(answer):
            return
        await message.reply(answer, mention_author=False)
        if not current_request(message.guild, version) or not current_reply(answer):
            return
        notice = accept(message.guild.id if message.guild else 0, answer)
        if notice:
            await message.reply(notice, mention_author=False)
        if message.guild:
            await speak_with_refresh(message.guild, message.channel, question, answer, version)


bot = CoachBot()


def begin_request(guild: discord.Guild | None) -> int:
    guild_id = guild.id if guild else 0
    version = bot.request_versions.get(guild_id, 0) + 1
    bot.request_versions[guild_id] = version
    pending = bot.generations.pop(guild_id, None)
    if pending and not pending.done():
        pending.cancel()
    voice = guild.voice_client if guild else None
    if voice and voice.is_playing():
        voice.stop()
    return version


def current_request(guild: discord.Guild | None, version: int) -> bool:
    return bot.request_versions.get(guild.id if guild else 0) == version


def current_reply(answer) -> bool:
    topic = getattr(answer, "topic", None) or getattr(answer, "explained_topic", None)
    return (not topic or topic.match_key is None or
            (topic.match_key == bot.coordinators.match_key and topic.serial == bot.coordinators.match_serial))


def stop_asked(question: str) -> bool:
    return quick_intent(question) == ("stop", None)


def silence(guild: discord.Guild | None, heard: str) -> None:
    """Stop: cut the audio and invalidate anything in flight. Nothing is posted, spoken or stored."""
    version = begin_request(guild)
    bot.stopped_versions[guild.id if guild else 0] = version
    print(f"Stop heard: {heard!r}", flush=True)


def drop_topic(guild_id: int) -> None:
    for store in (bot.topics, bot.topic_at, bot.topic_read_at):
        store.pop(guild_id, None)


def live_topic(guild_id: int) -> Topic | None:
    """The read "explain more" would elaborate on, while it is still this match and still recent."""
    topic = bot.topics.get(guild_id)
    if topic is None:
        return None
    now = time.monotonic()
    if ((topic.match_key, topic.serial) == (bot.coordinators.match_key, bot.coordinators.match_serial)
            and now - bot.topic_at.get(guild_id, now) <= TOPIC_SECONDS
            and now - bot.topic_read_at.get(guild_id, now) <= TOPIC_MAX_SECONDS):
        return topic
    drop_topic(guild_id)
    return None


def accept(guild_id: int, answer: str) -> str:
    """Record an answer after Discord sent it and its request gate was rechecked.
    A failed delivery, superseded answer or changed match cannot change its plan/topic.

    Returns a line to post after the answer when the player's note could not be written, otherwise ""."""
    if getattr(answer, "_accepted", False):
        return ""
    if not current_reply(answer):
        return ""
    if hasattr(answer, "__dict__"):
        answer._accepted = True
    if getattr(answer, "layer", 0):
        topic = bot.topics.get(guild_id)
        if topic:
            topic.layer = answer.layer
            bot.topic_at[guild_id] = time.monotonic()
            # "The first one" still answers the offer just explained. The board is shared and topics are
            # per guild, so the offer is kept alive only when it is the pair this explanation was about.
            if bot.coordinators.plan_state()[1][:2] == tuple((option.key, option.plan) for option in topic.pair):
                bot.coordinators.refresh_offer()
        return ""
    commit = getattr(answer, "commit", None)
    problem = commit() if commit else ""
    topic = getattr(answer, "topic", None)
    if topic is None:
        drop_topic(guild_id)
    else:
        topic.layer = 0
        bot.topics[guild_id] = topic
        bot.topic_read_at[guild_id] = bot.topic_at[guild_id] = time.monotonic()
    return problem if isinstance(problem, str) else ""


def live_teams() -> dict[str, list[str]] | None:
    """Champion names per team from the live feed, used to name minimap icons."""
    try:
        state = summarize_game(read_live_game())
    except (OSError, ValueError):
        return None
    teams: dict[str, list[str]] = {}
    for player in state["players"]:
        if player.get("team") and player.get("champion"):
            teams.setdefault(player["team"], []).append(player["champion"])
    return teams or None


async def make_answer(guild_id: int, question: str) -> str:
    started = time.perf_counter()
    try:
        route = await asyncio.to_thread(route_question, question)
    except IntentRouterError as error:
        print(f"Intent layer blocked request before JEV: {error}", flush=True)
        return ("I couldn't classify that request through OpenAI, so I did not send it to JEV. "
                "Check the intent logs and try again.")
    profiles = bot.models.frozen_chain(bot.models.selected(guild_id))
    profile = profiles[0]
    jev_config = dict(bot.models.data["jev"])
    version = bot.request_versions.get(guild_id)
    revision = bot.models.revision.get(guild_id, 0)
    topic = live_topic(guild_id)
    command = quick_intent(question, topic.words if topic else ((), ()))
    if command and command[0] == "more":
        if topic:
            # The next layer on the read already delivered: no feed read, no ranker, no board write.
            answer = explain(topic, command[1])
            answer.explained_topic = topic
            answer.generation_context = getattr(topic, "generation_context", {})
            return await apply_models(guild_id, question, answer, profiles, jev_config, started, version, revision)
        question = DEFAULT_QUESTION   # nothing recent to explain, so a fresh read
    route_details = f"Question route: {route.kind} via {route.source}"
    if route.tools:
        route_details += f"; tools={','.join(route.tools)}"
    print(route_details, flush=True)
    if route.kind == "clarify":
        return route.clarification
    if route.kind in {"observe", "estimate"}:
        state = bot.coordinators.last_state
        if state is None:
            try:
                state = summarize_game(await asyncio.to_thread(read_live_game))
            except (OSError, ValueError):
                state = None
        sightings = bot.minimap.snapshot() if bot.minimap else None
        answer = answer_tools(
            route.tools,
            state,
            sightings,
            minimap_enabled=bot.minimap is not None,
            minimap_error=bot.minimap.error if bot.minimap else None,
        )
        print(f"Local answer ({', '.join(route.tools)} via {route.source}) ready in "
              f"{time.perf_counter() - started:.1f}s", flush=True)
        return answer
    sightings = bot.minimap.snapshot() if bot.minimap else None
    # The board and the note file change in accept(), once the answer is delivered.
    deadline = bot.models.data["turn_deadline_seconds"]
    try:
        async with asyncio.timeout(deadline):
            answer = await asyncio.to_thread(coach, question, bot.style.get(guild_id, "balanced"),
                                             allow_demo_fallback=os.getenv("COACH_MOCK") == "1",
                                             coordinator_board=bot.coordinators, minimap=sightings,
                                             defer_board=True, champion_ask=True, scoreboard_reader=bot.scoreboard)
    except TimeoutError:
        return "The game read timed out. I won't give you an old call; ask again."
    answer = await apply_models(guild_id, question, answer, profiles, jev_config, started, version, revision)
    print(f"Answer ready in {time.perf_counter() - started:.1f}s", flush=True)
    return answer


async def apply_models(guild_id, question, answer, profiles, jev_config, started, version, revision):
    if (version == bot.request_versions.get(guild_id) and
            revision == bot.models.revision.get(guild_id, 0) and profiles[0]["provider"] != "builtin"):
        task = asyncio.create_task(enhance_chain(answer, question, profiles, jev_config,
                                          max(.01, bot.models.data["turn_deadline_seconds"] - (time.perf_counter() - started))))
        bot.generations[guild_id] = task
        try:
            answer = await task
        except asyncio.CancelledError:
            # The request/version gate suppresses the obsolete prepared answer too.
            return answer
        finally:
            if bot.generations.get(guild_id) is task:
                bot.generations.pop(guild_id, None)
    return answer


def material_game_signature() -> tuple | None:
    """Track changes that can invalidate a spoken call, without reacting to every CS tick."""
    try:
        state = summarize_game(read_live_game())
    except (OSError, ValueError):
        return None
    players = tuple(sorted((str(player["name"]), player["dead"], player["level"],
                            tuple(player["items"]))
                           for player in state["players"]))
    objectives = tuple((event["name"], event["time"], event["killer_team"])
                       for event in state["objective_events"])
    low_health = (state["active_health_percent"] is not None and
                  state["active_health_percent"] < 30)
    return state["active_player"], players, objectives, low_health


async def live_signature() -> tuple | None:
    return await asyncio.to_thread(material_game_signature)


def synthesize_windows(text: str, path: Path) -> None:
    """Use local Windows speech synthesis for the voice-channel reply."""
    script = Path(__file__).with_name("speak.ps1")
    subprocess.run(["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass",
                    "-File", str(script), str(path), text],
                   check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, timeout=20)


def spoken_script(message: str) -> str:
    """Return a short TTS-safe line for every response, not only successful game reads."""
    spoken = getattr(message, "spoken", "")
    if spoken:
        return spoken
    lines = [line.replace("**", "").partition(" — ")[0].strip().rstrip(".")
             for line in message.splitlines()[1:]]
    labels = ". ".join(line for line in lines if line)
    if labels:
        return labels + "."
    # Errors and status replies are commonly one line. Speaking them confirms that a wake-word
    # request reached Coach even when there is no live match or Jev is temporarily unavailable.
    plain = str(message).replace("**", "").replace("`", "").strip()
    words = plain.split()
    if len(words) > 80:
        plain = " ".join(words[:80]).rstrip(".,;:!?") + "."
    return plain


class SpeechFeed(io.RawIOBase):
    """File-like source for FFmpeg. read() blocks until edge-tts sends the next audio chunk."""

    def __init__(self) -> None:
        super().__init__()
        self.chunks: queue.Queue[bytes | None] = queue.Queue()
        self.pending = b""
        self.bytes_fed = 0

    def readable(self) -> bool:
        return True

    def push(self, data: bytes) -> None:
        self.bytes_fed += len(data)
        self.chunks.put(data)

    def finish(self) -> None:
        # Always called when playback ends, so the FFmpeg writer thread never waits forever.
        self.chunks.put(None)

    def read(self, size: int = -1) -> bytes:
        while not self.pending:
            chunk = self.chunks.get()
            if chunk is None:
                return b""
            self.pending = chunk
        if size is None or size < 0:
            size = len(self.pending)
        data, self.pending = self.pending[:size], self.pending[size:]
        return data


async def stream_speech(spoken: str, feed: SpeechFeed) -> None:
    """Stream the neural voice into playback as it arrives; use Windows speech only if no audio came back."""
    started = time.perf_counter()
    try:
        async with asyncio.timeout(30):
            communicate = edge_tts.Communicate(
                spoken,
                voice=os.getenv("COACH_VOICE", "en-US-SteffanNeural"),
                rate=os.getenv("COACH_VOICE_RATE", "+30%"),
                pitch=os.getenv("COACH_VOICE_PITCH", "-6Hz"),
                volume=os.getenv("COACH_VOICE_VOLUME", "+5%"),
            )
            async for chunk in communicate.stream():
                if chunk["type"] == "audio" and chunk["data"]:
                    if not feed.bytes_fed:
                        # If this grows with the length of the text, synthesize sentence by sentence.
                        print(f"First audio in {time.perf_counter() - started:.1f} s", flush=True)
                    feed.push(chunk["data"])
        if feed.bytes_fed == 0:
            raise RuntimeError("edge-tts returned no audio")
    except Exception as exc:
        if feed.bytes_fed:
            print(f"Neural voice stopped early ({type(exc).__name__}); the rest of the call is cut.", flush=True)
            return
        print(f"Neural voice failed ({type(exc).__name__}); using Windows speech.", flush=True)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "coach.wav"
            await asyncio.to_thread(synthesize_windows, spoken, path)
            feed.push(path.read_bytes())
    finally:
        feed.finish()


async def speak(guild: discord.Guild, message: str, version: int) -> str | None:
    voice = guild.voice_client
    if voice is None or not voice.is_connected():
        return None
    if not current_request(guild, version):
        return None
    if voice.is_playing():
        return "Voice is busy; the call is posted in chat."
    spoken = spoken_script(message)
    if not spoken:
        return None
    if not current_request(guild, version):
        return None
    feed = SpeechFeed()
    producer = asyncio.create_task(stream_speech(spoken, feed))
    started = time.perf_counter()
    try:
        source = discord.FFmpegOpusAudio(feed, pipe=True, executable=imageio_ffmpeg.get_ffmpeg_exe())
        done = asyncio.Event()
        loop = asyncio.get_running_loop()
        playback_error: list[Exception] = []

        def finished(error: Exception | None) -> None:
            if error:
                playback_error.append(error)
            loop.call_soon_threadsafe(done.set)

        voice.play(source, after=finished)
        for _ in range(90):
            try:
                await asyncio.wait_for(done.wait(), timeout=1)
                break
            except TimeoutError:
                if not current_request(guild, version):
                    voice.stop()
                    return None
        else:
            voice.stop()
            raise TimeoutError("Voice playback timed out")
        if playback_error:
            raise playback_error[0]
        print(f"Spoken call finished in {time.perf_counter() - started:.1f}s", flush=True)
    except Exception as exc:
        return f"Voice playback failed ({type(exc).__name__}); the call is posted in chat."
    finally:
        # Stops the writer thread and any unfinished synthesis when a newer question supersedes this one.
        producer.cancel()
        feed.finish()
        producer_result, = await asyncio.gather(producer, return_exceptions=True)
        if isinstance(producer_result, Exception):
            print(f"Speech synthesis failed: {type(producer_result).__name__}: {producer_result}", flush=True)
    return None


async def speak_with_refresh(guild: discord.Guild, channel: discord.abc.Messageable,
                             question: str, answer: str, version: int) -> str | None:
    # A completed call is allowed to finish. Game updates during playback are
    # frequent and restarting speech made Coach cut himself off repeatedly.
    # A newer player question still interrupts immediately via begin_request().
    return await speak(guild, answer, version)


async def silence_interaction(interaction: discord.Interaction, heard: str) -> None:
    """A slash "stop": silence first, then remove the command's own response so nothing is left in chat."""
    silence(interaction.guild, heard)
    try:
        await interaction.response.defer(ephemeral=True)
        await interaction.delete_original_response()
    except discord.HTTPException:
        pass   # the stop has already taken effect; at worst the invoker's private placeholder stays


async def respond_to_question(interaction: discord.Interaction, question: str) -> None:
    if stop_asked(question):
        await silence_interaction(interaction, question)
        return
    # The version is taken before the first await, so a stop that lands during the defer still wins.
    version = begin_request(interaction.guild)
    await interaction.response.defer(thinking=True)
    guild_id = interaction.guild_id or 0
    message = await make_answer(guild_id, question)
    if not current_request(interaction.guild, version) or not current_reply(message):
        # Replaced by a stop, or by a key press that may turn out to be one: leave nothing behind.
        latest = bot.request_versions.get(guild_id)
        if latest in (bot.stopped_versions.get(guild_id), bot.hotkey_versions.get(guild_id)):
            await interaction.delete_original_response()
        else:
            await interaction.followup.send("A newer question replaced this call.", ephemeral=True)
        return
    await interaction.followup.send(message)
    if not current_request(interaction.guild, version) or not current_reply(message):
        return
    notice = accept(guild_id, message)
    if notice:
        await interaction.followup.send(notice, ephemeral=True)
    if interaction.guild:
        voice_error = await speak_with_refresh(interaction.guild, interaction.channel,
                                               question, message, version)
        if voice_error:
            await interaction.followup.send(voice_error, ephemeral=True)


async def process_voice_question(guild: discord.Guild, user_id: int,
                                 name: str, pcm: bytes, *, local: bool = False,
                                 version_at_press: int | None = None) -> None:
    if guild.id not in bot.listen_channels:
        return
    try:
        heard_at = bot.request_versions.get(guild.id, 0)
        transcript = await asyncio.to_thread(transcribe_pcm, pcm, 1 if local else 2)
        question = question_after_wake(transcript)
        if local and not question:
            question = transcript.strip(" .,!?:;-\n\t")
        if not local and not question:
            # Nothing after a wake word. "Stop, coach." is still addressed to the coach and always counts;
            # with no wake word at all, a bare "stop" counts only while the coach is speaking.
            voice = guild.voice_client
            if stop_asked(transcript) and (WAKE.search(transcript) or
                                           (LISTEN_BARE_STOP and voice and voice.is_playing())):
                silence(guild, transcript)
            return
        if not question or guild.id not in bot.listen_channels:
            return
        if is_noise(question):   # breath, a filler word or one of Whisper's silence phrases: no reply
            return
        if stop_asked(question):
            if local:
                # Key-down already cut the audio and invalidated the answer in flight. The version is not
                # bumped again, so a late transcript cannot cancel a newer request.
                if version_at_press is not None:
                    bot.stopped_versions[guild.id] = version_at_press
                print(f"Stop heard: {question!r}", flush=True)
            else:
                silence(guild, question)
            return
        if not local and bot.request_versions.get(guild.id, 0) != heard_at:
            return   # a stop or a newer request landed while Whisper was still on this one
        version = version_at_press if local else begin_request(guild)
        if version is None or not current_request(guild, version):
            return
        channel = bot.listen_channels[guild.id]
        await channel.send(f"**{name} asked in voice:** {question}")
        answer = await make_answer(guild.id, question)
        if not current_request(guild, version) or not current_reply(answer):
            return
        await channel.send(answer)
        if not current_request(guild, version) or not current_reply(answer):
            return
        notice = accept(guild.id, answer)
        if notice:
            await channel.send(notice)
        voice_error = await speak_with_refresh(guild, channel, question, answer, version)
        if voice_error:
            await channel.send(voice_error)
    except Exception as exc:
        print(f"Voice question failed: {type(exc).__name__}: {exc}", flush=True)


def submit_voice(guild: discord.Guild, user_id: int, name: str, pcm: bytes) -> None:
    asyncio.run_coroutine_threadsafe(
        process_voice_question(guild, user_id, name, pcm), bot.loop)


def hotkey_pressed(guild: discord.Guild) -> None:
    future = asyncio.run_coroutine_threadsafe(interrupt_for_hotkey(guild), bot.loop)
    try:
        future.result(timeout=2)
    except Exception as exc:
        print(f"Hotkey interrupt failed: {type(exc).__name__}: {exc}", flush=True)


async def interrupt_for_hotkey(guild: discord.Guild) -> int:
    # The bump and its record are one step on the loop, so an answer that loses its gate to this key press
    # always sees the press as what replaced it.
    version = begin_request(guild)
    bot.hotkey_versions[guild.id] = version
    return version


def hotkey_released(guild: discord.Guild, name: str, pcm: bytes) -> None:
    version = bot.hotkey_versions.get(guild.id)
    asyncio.run_coroutine_threadsafe(
        process_voice_question(guild, 0, name, pcm, local=True, version_at_press=version), bot.loop)


@bot.tree.command(name="coach", description="Get the current read and an alternative from the live game")
@app_commands.describe(question="What does the team want to decide?")
async def coach_play(interaction: discord.Interaction, question: str = DEFAULT_QUESTION) -> None:
    await respond_to_question(interaction, question)


@bot.tree.command(name="models", description="List Coach's model profiles and configuration status")
async def models(interaction: discord.Interaction) -> None:
    lines = []
    for name in bot.models.data["profiles"]:
        profile = bot.models.frozen(name)
        lines.append(f"**{name}**: {profile['provider']}, {profile.get('model') or 'no model ID'} — "
                     f"{bot.models.readiness(name)}")
    lines.append("Generative profiles require a calibrated Jev policy for live speech. /compare tests drafts without speaking.")
    await interaction.response.send_message("\n".join(lines)[:1900], ephemeral=True)


@bot.tree.command(name="model", description="Inspect or change the Coach model for this server")
@app_commands.describe(use="Profile from /models", reset="Restore the default profile",
                       reload="Reload coach_models.json after editing it")
async def model(interaction: discord.Interaction, use: str | None = None,
                reset: bool = False, reload: bool = False) -> None:
    guild_id = interaction.guild_id or 0
    if use or reset or reload:
        if not interaction.guild or not interaction.permissions.manage_guild:
            await interaction.response.send_message("Manage Server is required to change Coach's model.", ephemeral=True)
            return
        if use and reset:
            await interaction.response.send_message("Choose either use or reset.", ephemeral=True)
            return
        try:
            if reload:
                bot.models.reload()
                for guild in bot.guilds:
                    begin_request(guild)
            if use or reset:
                bot.models.select(guild_id, use if use else None)
            begin_request(interaction.guild)
        except (OSError, ValueError, KeyError, TypeError):
            await interaction.response.send_message("Model configuration rejected. Check the local config and /models.", ephemeral=True)
            return
    selected = bot.models.selected(guild_id)
    profile = bot.models.frozen(selected)
    config = bot.models.data["jev"]
    await interaction.response.send_message(
        f"Coach profile: **{selected}** ({profile['provider']}; {profile.get('model') or 'prepared wording'}).\n"
        f"Status: {bot.models.readiness(selected)}. Jev guard: {config['model']}.\n"
        f"Calibration: {config.get('policy_id') or 'none — generated wording is comparison-only'}.\n"
        "Use /model use:<profile> to switch or /model reset:true to restore the default.", ephemeral=True)


@model.autocomplete("use")
async def model_choices(interaction: discord.Interaction, current: str):
    return [app_commands.Choice(name=name, value=name) for name in bot.models.data["profiles"]
            if current.casefold() in name.casefold()][:25]


@bot.tree.command(name="compare", description="Compare up to three LLM drafts on one game snapshot; no speech or plan writes")
@app_commands.describe(profiles="Comma-separated profiles from /models", question="Question to compare")
async def compare(interaction: discord.Interaction, profiles: str,
                  question: str = DEFAULT_QUESTION) -> None:
    names = list(dict.fromkeys(name.strip() for name in profiles.split(",") if name.strip()))
    try:
        if not 1 <= len(names) <= 3:
            raise ValueError("Choose one to three profiles")
        selected = [bot.models.frozen(name) for name in names]
        if any(bot.models.readiness(name) != "ready" for name in names):
            raise ValueError("A profile is disabled or missing configuration")
    except (ValueError, KeyError) as exc:
        await interaction.response.send_message(str(exc), ephemeral=True)
        return
    await interaction.response.defer(thinking=True, ephemeral=True)
    common_budget = min(profile["max_output_tokens"] for profile in selected)
    for profile in selected:
        profile["max_output_tokens"] = common_budget
    # A separate board avoids writing live plans/notes while building this frozen evaluation brief.
    board = bot.coordinators.fork()
    answer = await asyncio.to_thread(coach, question, bot.style.get(interaction.guild_id or 0, "balanced"),
                                     coordinator_board=board, defer_board=True,
                                     minimap=bot.minimap.snapshot() if bot.minimap else None,
                                     scoreboard_reader=bot.scoreboard)
    if not getattr(answer, "generation_context", None):
        await interaction.followup.send(str(answer), ephemeral=True)
        return
    brief = brief_for(answer, question)
    config = dict(bot.models.data["jev"])
    async def run(profile):
        if profile["provider"] == "builtin":
            return f"**{profile['id']}** — prepared Jev wording\n{getattr(answer, 'spoken', str(answer))}"
        try:
            async with asyncio.timeout(bot.models.data["turn_deadline_seconds"]):
                result, checked = await draft(profile, brief, config, 5)
            hazards = ", ".join(f"{name}={checked['answers'][name]['noul']:.2f}"
                                for name in ("unseen_location", "unsupported_number", "missed_question"))
            return (f"**{profile['id']}** ({result.model}, {result.seconds:.2f}s generation)\n"
                    f"UNVALIDATED DRAFT: {result.text}\nJev: {hazards}; usage: {result.usage}")
        except Exception as exc:
            return f"**{profile['id']}**: comparison failed ({type(exc).__name__})."
    results = await asyncio.gather(*(run(profile) for profile in selected))
    for result in results:
        await interaction.followup.send(result[:1900], ephemeral=True)


@bot.tree.command(name="scoreboard", description="Check automatic scoreboard screenshot capture and text reading")
async def scoreboard(interaction: discord.Interaction) -> None:
    if not bot.scoreboard:
        await interaction.response.send_message("Scoreboard capture is disabled on the host PC.", ephemeral=True)
        return
    status = bot.scoreboard.status()
    await interaction.response.send_message(
        f"Scoreboard capture {'running' if status['active'] else 'stopped'}; key {status['key']} (Tab by default).\n"
        f"Saved captures: {status['captures']}. {status['last_status']}. "
        f"Age: {status['age_seconds'] if status['age_seconds'] is not None else 'none'} seconds.\n"
        f"{status['error']}\nHold Tab in the foreground League game. Fresh readable text feeds Jev and the selected model. "
        "OCR is unverified; API facts take priority. Screenshots stay on this PC.", ephemeral=True)


@bot.tree.command(name="stop", description="Stop the coach talking and cancel the answer in progress")
async def stop(interaction: discord.Interaction) -> None:
    await silence_interaction(interaction, "/stop")


@bot.tree.command(name="note", description="Save, in your own words, how you play the champion you are on")
@app_commands.describe(text="One sentence on how you play it; leave blank to list your notes")
async def note(interaction: discord.Interaction, text: str = "") -> None:
    state = bot.coordinators.last_state
    champion = active_champion(state) if state else None
    if not champion:
        await interaction.response.send_message(
            "No live match, so I don't know which champion this is for.", ephemeral=True)
        return
    if not text.strip():
        notes = await asyncio.to_thread(lane_playbook.champion_notes, champion)
        message = (f"Your notes on {champion} (your own words): " + " | ".join(notes) if notes else
                   f"No notes on {champion} yet. Use /note with one sentence on how you play it.")
    else:
        try:
            stored = await asyncio.to_thread(lane_playbook.add_champion_note, champion, active_role(state), text)
            message = (f"Saved for {champion}, in your own words: \"{stored}\" "
                       "(edit lane_playbook\\champion_notes.md)." if stored else "That note was empty; nothing saved.")
        except OSError as exc:
            print(f"Champion note not saved: {type(exc).__name__}: {exc}", flush=True)
            message = NOTE_NOT_SAVED
    await interaction.response.send_message(message, ephemeral=True)


@bot.tree.command(name="ask", description="Ask the coach a specific question")
@app_commands.describe(question="For example: should we contest dragon or trade?")
async def ask(interaction: discord.Interaction, question: str) -> None:
    await respond_to_question(interaction, question)


@bot.tree.command(name="state", description="Show what the coach can read from this match")
async def state(interaction: discord.Interaction) -> None:
    await interaction.response.defer(thinking=True)
    try:
        snapshot = await asyncio.to_thread(read_live_game)
        summary = summarize_game(snapshot)
        if not summary["our_team"] or len(summary["players"]) < 2:
            message = "The live feed is missing player or team data."
        else:
            message = "Live game data: " + evidence(summary) + "."
    except (OSError, ValueError):
        message = "I can't read a live League match on this PC right now."
    await interaction.followup.send(message)


@bot.tree.command(name="coordinators", description="Read the five role coordinators' live notes")
@app_commands.choices(role=[app_commands.Choice(name=s.title(), value=s)
                            for s in ("top", "jungle", "mid", "bot", "support")])
async def coordinators(interaction: discord.Interaction,
                       role: app_commands.Choice[str] | None = None) -> None:
    try:
        snapshot = await asyncio.to_thread(read_live_game)
        bot.coordinators.observe(summarize_game(snapshot))
    except (OSError, ValueError):
        pass
    message = bot.coordinators.display(role.value if role else None)
    state = bot.coordinators.last_state
    champion = active_champion(state) if state else None
    notes = lane_playbook.champion_notes(champion) if champion else []
    if notes:
        message += f"\n**Your note on {champion}** (your own words): " + " | ".join(notes)
    await interaction.response.send_message(message)


@bot.tree.command(description="Set your team's preferred approach")
@app_commands.choices(style=[app_commands.Choice(name=s, value=s)
                             for s in ("aggressive", "balanced", "cautious")])
async def approach(interaction: discord.Interaction, style: app_commands.Choice[str]) -> None:
    bot.style[interaction.guild_id or 0] = style.value
    await interaction.response.send_message(f"Team approach: {style.value}.")


@bot.tree.command(description="Join your current voice channel")
async def join(interaction: discord.Interaction) -> None:
    channel = getattr(getattr(interaction.user, "voice", None), "channel", None)
    if channel is None:
        await interaction.response.send_message("Join a voice channel first.", ephemeral=True)
        return
    try:
        if interaction.guild and interaction.guild.voice_client:
            await interaction.guild.voice_client.move_to(channel)
        else:
            await channel.connect(cls=voice_recv.VoiceRecvClient)
    except (discord.DiscordException, OSError) as exc:
        await interaction.response.send_message(f"Could not join voice: {type(exc).__name__}.", ephemeral=True)
        return
    await interaction.response.send_message(
        "Joined voice. Use /coach for a spoken call, or /listen to ask by speaking.")


@bot.tree.command(name="listen", description="Listen for 'Coach, ...' in this voice call")
async def listen(interaction: discord.Interaction) -> None:
    channel = getattr(getattr(interaction.user, "voice", None), "channel", None)
    if channel is None or interaction.guild is None:
        await interaction.response.send_message("Join a voice channel first.", ephemeral=True)
        return
    await interaction.response.defer(thinking=True)
    try:
        old_hotkey = bot.hotkeys.pop(interaction.guild.id, None)
        if old_hotkey:
            await asyncio.to_thread(old_hotkey.stop)
        await asyncio.to_thread(load_model)
        voice = interaction.guild.voice_client
        if voice and not isinstance(voice, voice_recv.VoiceRecvClient):
            await voice.disconnect()
            voice = None
        if voice and voice.channel != channel:
            await voice.move_to(channel)
        elif voice is None:
            voice = await channel.connect(cls=voice_recv.VoiceRecvClient)
        if not voice.is_listening():
            sink = CoachSink(lambda user_id, name, pcm:
                             submit_voice(interaction.guild, user_id, name, pcm))
            voice.listen(sink)
            bot.listen_sinks[interaction.guild.id] = sink
        bot.listen_channels[interaction.guild.id] = interaction.channel
    except Exception as exc:
        await interaction.followup.send(f"Could not start listening: {type(exc).__name__}.")
        return
    await interaction.followup.send(
        "Listening in voice now. Say **'Coach, should we contest dragon?'** or another question. "
        "I will post the transcript and answer here. Use `/stoplisten` to stop listening.")


@bot.tree.command(name="miclist", description="Show local microphones for Coach push-to-talk")
async def miclist(interaction: discord.Interaction) -> None:
    devices = await asyncio.to_thread(input_devices)
    lines = [f"{index}: {name}" for index, name in devices]
    await interaction.response.send_message("Local input devices:\n" + "\n".join(lines[:20]), ephemeral=True)


@bot.tree.command(name="hotkey", description="Hold the - key on this PC to ask Coach without Discord voice receive")
@app_commands.describe(mic="Optional input device number from /miclist; blank uses Windows default")
async def hotkey(interaction: discord.Interaction, mic: int | None = None) -> None:
    channel = getattr(getattr(interaction.user, "voice", None), "channel", None)
    if channel is None or interaction.guild is None:
        await interaction.response.send_message("Join a voice channel first.", ephemeral=True)
        return
    await interaction.response.defer(thinking=True)
    try:
        await asyncio.to_thread(load_model)
        for old in list(bot.hotkeys.values()):
            await asyncio.to_thread(old.stop)
        bot.hotkeys.clear()
        voice = interaction.guild.voice_client
        if isinstance(voice, voice_recv.VoiceRecvClient):
            if voice.is_listening():
                voice.stop_listening()
            await voice.disconnect()
            voice = None
        if voice and voice.channel != channel:
            await voice.move_to(channel)
        elif voice is None:
            await channel.connect()
        bot.listen_sinks.pop(interaction.guild.id, None)
        bot.listen_channels[interaction.guild.id] = interaction.channel
        capture = HotkeyCapture(
            lambda: hotkey_pressed(interaction.guild),
            lambda pcm: hotkey_released(interaction.guild, interaction.user.display_name, pcm),
            device=mic,
        )
        await asyncio.to_thread(capture.start)
        bot.hotkeys[interaction.guild.id] = capture
    except Exception as exc:
        await interaction.followup.send(f"Hotkey could not start: {type(exc).__name__}: {exc}", ephemeral=True)
        return
    await interaction.followup.send(
        "Coach-only push-to-talk is on. **Hold the - key (between 0 and =) on this PC**, speak your question, then release. "
        "Pressing it stops Coach immediately; you can still talk normally to friends in Discord. "
        "Use `/stophotkey` to turn it off.")


@bot.tree.command(name="stophotkey", description="Turn off Coach's local push-to-talk key")
async def stophotkey(interaction: discord.Interaction) -> None:
    if interaction.guild:
        capture = bot.hotkeys.pop(interaction.guild.id, None)
        if capture:
            await asyncio.to_thread(capture.stop)
        bot.listen_channels.pop(interaction.guild.id, None)
        drop_topic(interaction.guild.id)
    await interaction.response.send_message("Coach-only push-to-talk is off.")


@bot.tree.command(name="listenstatus", description="Check whether voice audio reaches the coach")
async def listenstatus(interaction: discord.Interaction) -> None:
    guild = interaction.guild
    voice = guild.voice_client if guild else None
    sink = bot.listen_sinks.get(guild.id) if guild else None
    capture = bot.hotkeys.get(guild.id) if guild else None
    if capture:
        message = (f"Local push-to-talk key {'is on' if capture.active else 'stopped'}; "
                   f"completed questions: {capture.questions}." +
                   (f" Mic error: {type(capture.error).__name__}." if capture.error else ""))
    elif not isinstance(voice, voice_recv.VoiceRecvClient) or not voice.is_listening() or sink is None:
        message = "Voice listening is off. Run /listen while in the call."
    else:
        message = (f"Listening is on. Decoded audio: {sink.pcm_bytes // 1000} KB; "
                   f"speech segments: {sink.completed_segments}. "
                   "Speak for a second, then check this again.")
    await interaction.response.send_message(message, ephemeral=True)


@bot.tree.command(name="stoplisten", description="Stop listening to this voice call")
async def stoplisten(interaction: discord.Interaction) -> None:
    if interaction.guild:
        capture = bot.hotkeys.pop(interaction.guild.id, None)
        if capture:
            await asyncio.to_thread(capture.stop)
        bot.listen_channels.pop(interaction.guild.id, None)
        bot.listen_sinks.pop(interaction.guild.id, None)
        drop_topic(interaction.guild.id)
        voice = interaction.guild.voice_client
        if isinstance(voice, voice_recv.VoiceRecvClient) and voice.is_listening():
            voice.stop_listening()
    await interaction.response.send_message("Stopped listening. I can still speak when asked in text.")


@bot.tree.command(description="Leave the voice channel")
async def leave(interaction: discord.Interaction) -> None:
    if interaction.guild:
        capture = bot.hotkeys.pop(interaction.guild.id, None)
        if capture:
            await asyncio.to_thread(capture.stop)
        bot.listen_channels.pop(interaction.guild.id, None)
        bot.listen_sinks.pop(interaction.guild.id, None)
        drop_topic(interaction.guild.id)
    voice = interaction.guild.voice_client if interaction.guild else None
    if voice:
        await voice.disconnect()
    await interaction.response.send_message("Left voice.")


if __name__ == "__main__":
    try:
        bot.run(load_discord_token())
    except RuntimeError as exc:
        raise SystemExit(str(exc)) from None
