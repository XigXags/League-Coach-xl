"""A new call must replace speech and suppress older answers."""

import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

import bot as coach_bot
from coach import Option, Reply, Topic, explain


class VoiceStub:
    def __init__(self):
        self.stops = 0

    def is_playing(self):
        return True

    def stop(self):
        self.stops += 1


class InterruptTests(unittest.IsolatedAsyncioTestCase):
    def test_new_request_stops_speech_and_invalidates_previous_result(self):
        voice = VoiceStub()
        guild = SimpleNamespace(id=987654, voice_client=voice)
        first = coach_bot.begin_request(guild)
        second = coach_bot.begin_request(guild)
        self.assertFalse(coach_bot.current_request(guild, first))
        self.assertTrue(coach_bot.current_request(guild, second))
        self.assertEqual(voice.stops, 2)

    async def test_game_update_does_not_restart_speech(self):
        guild = SimpleNamespace(id=987655, voice_client=None)
        channel = SimpleNamespace(send=AsyncMock())
        version = coach_bot.begin_request(guild)
        with patch.object(coach_bot, "speak", new_callable=AsyncMock,
                          return_value=None) as speak:
            with patch.object(coach_bot, "make_answer", new_callable=AsyncMock,
                              return_value="Game read (live game): updated") as answer:
                result = await coach_bot.speak_with_refresh(
                    guild, channel, "What now?", "Game read (live game): old", version)
        self.assertIsNone(result)
        answer.assert_not_awaited()
        speak.assert_awaited_once()
        channel.send.assert_not_awaited()

    async def test_local_hotkey_question_needs_no_wake_word(self):
        guild = SimpleNamespace(id=987656, voice_client=None)
        channel = SimpleNamespace(send=AsyncMock())
        coach_bot.bot.listen_channels[guild.id] = channel
        version = coach_bot.begin_request(guild)
        try:
            with patch.object(coach_bot, "transcribe_pcm", return_value="Should we push mid?"), \
                 patch.object(coach_bot, "make_answer", new_callable=AsyncMock,
                              return_value="Game read (live game): answer"), \
                 patch.object(coach_bot, "speak_with_refresh", new_callable=AsyncMock,
                              return_value=None):
                await coach_bot.process_voice_question(guild, 0, "Player", b"pcm",
                                                       local=True, version_at_press=version)
            self.assertEqual(channel.send.await_count, 2)
            self.assertIn("Should we push mid", channel.send.await_args_list[0].args[0])
        finally:
            coach_bot.bot.listen_channels.pop(guild.id, None)


class QuietVoice(VoiceStub):
    def is_playing(self):
        return False


def a_topic(**changes):
    values = dict(match_key=coach_bot.bot.coordinators.match_key, serial=coach_bot.bot.coordinators.match_serial,
                  game_second=208, source="live game",
                  pair=(Option("a", "Alpha", "Push the wave. You check: the wave."),
                        Option("b", "Beta", "Reset now. You check: your gold.")),
                  more=(), names=("alpha", "beta"), words=(("alpha",), ("beta",)), lessons=(None, None),
                  background={})
    return Topic(**{**values, **changes})


def fresh_reply(commit=None):
    reply = Reply("Game read (live game): x.\n**Alpha** — r\nOtherwise: **Beta** — r\nYour call.")
    reply.spoken, reply.topic, reply.commit = "Alpha. Or, beta.", a_topic(), commit
    return reply


class StopAndMoreTests(unittest.IsolatedAsyncioTestCase):
    """Stop posts and speaks nothing on every path; "more" explains the delivered read without a new one."""
    _ids = iter(range(990000, 999999))

    def setUp(self):
        self.voice = None
        self.guild = SimpleNamespace(id=next(self._ids), voice_client=None)
        self.channel = SimpleNamespace(send=AsyncMock())
        coach_bot.bot.listen_channels[self.guild.id] = self.channel
        self.addCleanup(self._forget)

    def _forget(self):
        state = coach_bot.bot
        for store in (state.listen_channels, state.topics, state.topic_at, state.topic_read_at,
                      state.stopped_versions, state.hotkey_versions, state.request_versions):
            store.pop(self.guild.id, None)

    def _press(self):
        version = coach_bot.begin_request(self.guild)
        coach_bot.bot.hotkey_versions[self.guild.id] = version
        return version

    async def _voice(self, heard, *, local=True, version=None, answer="Game read (live game): answer"):
        with patch.object(coach_bot, "transcribe_pcm", return_value=heard), \
             patch.object(coach_bot, "make_answer", new_callable=AsyncMock, return_value=answer) as made, \
             patch.object(coach_bot, "speak_with_refresh", new_callable=AsyncMock, return_value=None) as spoke:
            await coach_bot.process_voice_question(self.guild, 0, "Player", b"pcm", local=local,
                                                   version_at_press=version)
        return made, spoke

    def _interaction(self):
        return SimpleNamespace(guild=self.guild, guild_id=self.guild.id, channel=self.channel,
                               response=SimpleNamespace(defer=AsyncMock()),
                               followup=SimpleNamespace(send=AsyncMock()),
                               delete_original_response=AsyncMock())

    async def test_a_hotkey_stop_posts_and_speaks_nothing(self):
        version = self._press()
        with patch("builtins.print"):
            made, spoke = await self._voice("Stop.", version=version)
        self.channel.send.assert_not_awaited()
        made.assert_not_awaited()
        spoke.assert_not_awaited()
        # The release does not bump the version again, so a late transcript cannot cancel a newer request.
        self.assertEqual(coach_bot.bot.request_versions[self.guild.id], version)
        self.assertEqual(coach_bot.bot.stopped_versions[self.guild.id], version)

    async def test_a_hotkey_silence_phrase_is_dropped(self):
        for heard in ("Thank you.", "you", "Okay."):
            made, _ = await self._voice(heard, version=self._press())
            made.assert_not_awaited()
        self.channel.send.assert_not_awaited()
        self.assertNotIn(self.guild.id, coach_bot.bot.stopped_versions)

    async def test_a_normal_hotkey_question_still_sends_the_echo_and_the_answer(self):
        made, spoke = await self._voice("Should we push mid?", version=self._press())
        self.assertEqual(self.channel.send.await_count, 2)
        made.assert_awaited_once_with(self.guild.id, "Should we push mid")
        spoke.assert_awaited_once()

    async def test_coach_stop_on_listen_silences_and_bumps_the_version(self):
        self.guild.voice_client = VoiceStub()
        before = coach_bot.begin_request(self.guild)
        with patch("builtins.print"):
            made, _ = await self._voice("Coach, stop.", local=False)
        self.channel.send.assert_not_awaited()
        made.assert_not_awaited()
        self.assertEqual(coach_bot.bot.request_versions[self.guild.id], before + 1)
        self.assertEqual(coach_bot.bot.stopped_versions[self.guild.id], before + 1)
        self.assertEqual(self.guild.voice_client.stops, 2)
        made, _ = await self._voice("Coach, thank you.", local=False)
        made.assert_not_awaited()
        self.assertEqual(coach_bot.bot.request_versions[self.guild.id], before + 1)

    async def test_a_bare_stop_on_listen_acts_only_while_the_coach_is_speaking(self):
        before = coach_bot.begin_request(self.guild)
        for voice in (None, QuietVoice()):
            self.guild.voice_client = voice
            await self._voice("Stop.", local=False)
            self.assertEqual(coach_bot.bot.request_versions[self.guild.id], before)
        self.guild.voice_client = VoiceStub()
        with patch("builtins.print"):
            await self._voice("Stop the dive now", local=False)   # a sentence, not the command
            self.assertEqual(coach_bot.bot.request_versions[self.guild.id], before)
            with patch.object(coach_bot, "LISTEN_BARE_STOP", False):
                await self._voice("Stop.", local=False)
            self.assertEqual(coach_bot.bot.request_versions[self.guild.id], before)
            made, _ = await self._voice("Stop.", local=False)
        self.assertEqual(coach_bot.bot.request_versions[self.guild.id], before + 1)
        self.assertEqual(self.guild.voice_client.stops, 1)
        made.assert_not_awaited()
        self.channel.send.assert_not_awaited()

    async def test_a_stop_with_the_wake_word_last_needs_no_speech_to_cut(self):
        self.guild.voice_client = QuietVoice()   # nothing playing: the answer is still being computed
        before = coach_bot.begin_request(self.guild)
        with patch("builtins.print"):
            for count, heard in enumerate(("Shut up, coach.", "Stop, coach.", "Coach."), start=1):
                made, _ = await self._voice(heard, local=False)
                made.assert_not_awaited()
                self.assertEqual(coach_bot.bot.request_versions[self.guild.id], before + min(count, 2), heard)
        self.channel.send.assert_not_awaited()
        self.assertEqual(coach_bot.bot.stopped_versions[self.guild.id], before + 2)

    async def test_a_stop_that_lands_while_whisper_is_working_wins(self):
        before = coach_bot.begin_request(self.guild)

        def slow(pcm, channels):
            coach_bot.silence(self.guild, "Coach, stop.")   # the shorter clip was transcribed first
            return "Coach, what now?"

        with patch.object(coach_bot, "transcribe_pcm", side_effect=slow), patch("builtins.print"), \
             patch.object(coach_bot, "make_answer", new_callable=AsyncMock) as made:
            await coach_bot.process_voice_question(self.guild, 0, "Player", b"pcm")
        made.assert_not_awaited()
        self.channel.send.assert_not_awaited()
        self.assertEqual(coach_bot.bot.request_versions[self.guild.id], before + 1)   # not bumped again

    async def test_a_stop_that_lands_while_a_slash_question_is_acknowledged_wins(self):
        interaction = self._interaction()
        commit = Mock()
        interaction.response.defer.side_effect = lambda **kwargs: coach_bot.silence(self.guild, "/stop")
        with patch.object(coach_bot, "make_answer", new_callable=AsyncMock, return_value=fresh_reply(commit)), \
             patch("builtins.print"), \
             patch.object(coach_bot, "speak_with_refresh", new_callable=AsyncMock) as spoke:
            await coach_bot.respond_to_question(interaction, "what now")
        interaction.followup.send.assert_not_awaited()
        interaction.delete_original_response.assert_awaited_once_with()
        spoke.assert_not_awaited()
        commit.assert_not_called()

    async def test_a_key_press_is_recorded_in_the_same_step_that_replaces_the_answer(self):
        version = await coach_bot.interrupt_for_hotkey(self.guild)
        self.assertEqual(coach_bot.bot.hotkey_versions[self.guild.id], version)
        self.assertEqual(coach_bot.bot.request_versions[self.guild.id], version)

    async def test_a_slash_stop_that_discord_rejects_still_stops_quietly(self):
        rejected = coach_bot.discord.HTTPException(SimpleNamespace(status=500, reason="down"), "down")
        for failing in ("defer", "delete"):
            interaction = self._interaction()
            if failing == "defer":
                interaction.response.defer.side_effect = rejected
            else:
                interaction.delete_original_response.side_effect = rejected
            before = coach_bot.bot.request_versions.get(self.guild.id, 0)
            with patch("builtins.print"):
                await coach_bot.respond_to_question(interaction, "stop")
            self.assertEqual(coach_bot.bot.stopped_versions[self.guild.id], before + 1)
            interaction.followup.send.assert_not_awaited()

    async def test_a_mention_stop_gets_no_reply(self):
        user = SimpleNamespace(id=42)
        message = SimpleNamespace(author=SimpleNamespace(bot=False), mentions=[user], content="<@42> stop",
                                  guild=self.guild, channel=self.channel, reply=AsyncMock())
        before = coach_bot.begin_request(self.guild)
        with patch.object(type(coach_bot.bot), "user", user), patch("builtins.print"), \
             patch.object(coach_bot, "make_answer", new_callable=AsyncMock) as made:
            await coach_bot.bot.on_message(message)
        message.reply.assert_not_awaited()
        made.assert_not_awaited()
        self.assertEqual(coach_bot.bot.stopped_versions[self.guild.id], before + 1)

    async def test_a_slash_stop_leaves_nothing_in_chat(self):
        for question in ("stop", "Shut up please"):
            interaction = self._interaction()
            with patch("builtins.print"), \
                 patch.object(coach_bot, "make_answer", new_callable=AsyncMock) as made:
                await coach_bot.respond_to_question(interaction, question)
            interaction.response.defer.assert_awaited_once_with(ephemeral=True)
            interaction.delete_original_response.assert_awaited_once_with()
            interaction.followup.send.assert_not_awaited()
            made.assert_not_awaited()
            self.assertEqual(coach_bot.bot.stopped_versions[self.guild.id],
                             coach_bot.bot.request_versions[self.guild.id])

    async def _slash_replaced_by(self, replace):
        interaction = self._interaction()
        commit = Mock()

        async def answer(guild_id, question):
            replace()   # something else happens while the answer is being computed
            return fresh_reply(commit)

        with patch.object(coach_bot, "make_answer", side_effect=answer), patch("builtins.print"), \
             patch.object(coach_bot, "speak_with_refresh", new_callable=AsyncMock) as spoke:
            await coach_bot.respond_to_question(interaction, "what now")
        spoke.assert_not_awaited()
        commit.assert_not_called()
        self.assertNotIn(self.guild.id, coach_bot.bot.topics)
        return interaction

    async def test_a_slash_answer_that_lost_to_a_stop_or_a_key_press_is_removed(self):
        for replace in (lambda: coach_bot.silence(self.guild, "stop"), self._press):
            interaction = await self._slash_replaced_by(replace)
            interaction.delete_original_response.assert_awaited_once_with()
            interaction.followup.send.assert_not_awaited()

    async def test_a_slash_answer_that_lost_to_a_question_still_says_so(self):
        interaction = await self._slash_replaced_by(lambda: coach_bot.begin_request(self.guild))
        interaction.delete_original_response.assert_not_awaited()
        interaction.followup.send.assert_awaited_once_with("A newer question replaced this call.", ephemeral=True)

    async def test_a_key_press_while_the_answer_is_computed_discards_it(self):
        commit = Mock()

        async def answer(guild_id, question):
            self._press()   # key-down with no release yet
            return fresh_reply(commit)

        with patch.object(coach_bot, "transcribe_pcm", return_value="what now"), \
             patch.object(coach_bot, "make_answer", side_effect=answer), \
             patch.object(coach_bot, "speak_with_refresh", new_callable=AsyncMock) as spoke:
            await coach_bot.process_voice_question(self.guild, 0, "Player", b"pcm", local=True,
                                                   version_at_press=self._press())
        self.assertEqual([call.args[0] for call in self.channel.send.await_args_list],
                         ["**Player asked in voice:** what now"])   # the echo; the answer never follows
        spoke.assert_not_awaited()
        commit.assert_not_called()
        self.assertNotIn(self.guild.id, coach_bot.bot.topics)

    async def test_a_delivered_answer_is_committed_before_it_is_sent(self):
        order = []
        reply = fresh_reply(lambda: order.append("commit"))
        self.channel.send.side_effect = lambda text: order.append("send")
        await self._voice("what now", version=self._press(), answer=reply)
        self.assertEqual(order, ["send", "commit", "send"])   # echo, commit, answer
        self.assertIs(coach_bot.bot.topics[self.guild.id], reply.topic)

    def test_accept_commits_a_fresh_read_and_remembers_its_topic(self):
        commit = Mock()
        reply = fresh_reply(commit)
        reply.topic.layer = 2
        with patch.object(coach_bot.time, "monotonic", return_value=500.0):
            coach_bot.accept(self.guild.id, reply)
        commit.assert_called_once_with()
        self.assertIs(coach_bot.bot.topics[self.guild.id], reply.topic)
        self.assertEqual(reply.topic.layer, 0)
        self.assertEqual((coach_bot.bot.topic_at[self.guild.id], coach_bot.bot.topic_read_at[self.guild.id]),
                         (500.0, 500.0))

    def test_accept_drops_the_topic_for_an_answer_that_is_not_a_read(self):
        coach_bot.accept(self.guild.id, fresh_reply())
        coach_bot.accept(self.guild.id, "I can't read a live League match on this PC right now.")
        for store in (coach_bot.bot.topics, coach_bot.bot.topic_at, coach_bot.bot.topic_read_at):
            self.assertNotIn(self.guild.id, store)
        kept = Reply("Jev is unavailable right now. I kept your note on Zac.")
        kept.commit = Mock()
        coach_bot.accept(self.guild.id, kept)
        kept.commit.assert_called_once_with()

    def test_accept_moves_the_layer_on_and_keeps_the_offer_answerable(self):
        with patch.object(coach_bot.time, "monotonic", return_value=500.0):
            coach_bot.accept(self.guild.id, fresh_reply())
        topic = coach_bot.bot.topics[self.guild.id]
        layer = explain(topic)
        self.assertEqual((layer.layer, topic.layer), (1, 0))
        board = coach_bot.bot.coordinators
        offered = (None, (("a", ""), ("b", ""), ("c", "third")), 100)   # the topic's pair, then a menu extra
        with patch.object(board, "refresh_offer") as refresh, patch.object(board, "plan_state", return_value=offered), \
             patch.object(coach_bot.time, "monotonic", return_value=530.0):
            self.assertEqual(coach_bot.accept(self.guild.id, layer), "")
        refresh.assert_called_once_with()
        self.assertEqual(topic.layer, 1)
        self.assertIs(coach_bot.bot.topics[self.guild.id], topic)
        self.assertEqual((coach_bot.bot.topic_at[self.guild.id], coach_bot.bot.topic_read_at[self.guild.id]),
                         (530.0, 500.0))
        with patch.object(board, "refresh_offer") as refresh, patch.object(board, "plan_state", return_value=offered):
            coach_bot.accept(self.guild.id + 1, layer)   # no topic stored for that guild: nothing to move
        refresh.assert_not_called()

    def test_an_explanation_does_not_keep_another_guilds_offer_alive(self):
        # The board is shared; the last offer on it may be a pair read out somewhere else.
        coach_bot.accept(self.guild.id, fresh_reply())
        topic = coach_bot.bot.topics[self.guild.id]
        board, layer = coach_bot.bot.coordinators, explain(topic)
        for offer in ((("b", ""), ("a", "")), (("x", "objective"), ("a", "")), ()):
            with patch.object(board, "refresh_offer") as refresh, \
                 patch.object(board, "plan_state", return_value=(None, offer, 100)):
                coach_bot.accept(self.guild.id, layer)
            refresh.assert_not_called()
        self.assertEqual(topic.layer, 1)   # the layer still moves on; only the offer is left alone

    def test_a_note_that_could_not_be_written_is_said_after_the_answer(self):
        reply = fresh_reply(lambda: "I could not write the note.")
        await_free = coach_bot.accept(self.guild.id, reply)
        self.assertEqual(await_free, "I could not write the note.")
        self.assertIs(coach_bot.bot.topics[self.guild.id], reply.topic)   # the answer itself is delivered as usual
        self.assertEqual(coach_bot.accept(self.guild.id, fresh_reply(Mock())), "")

    async def test_the_unsaved_note_line_follows_the_answer_on_every_path(self):
        reply = fresh_reply(lambda: "I could not write the note.")
        await self._voice("what now", version=self._press(), answer=reply)
        self.assertEqual([call.args[0] for call in self.channel.send.await_args_list][1:],
                         [reply, "I could not write the note."])
        interaction = self._interaction()
        with patch.object(coach_bot, "make_answer", new_callable=AsyncMock, return_value=reply), \
             patch.object(coach_bot, "speak_with_refresh", new_callable=AsyncMock, return_value=None):
            await coach_bot.respond_to_question(interaction, "what now")
        self.assertEqual([call.args[0] for call in interaction.followup.send.await_args_list],
                         [reply, "I could not write the note."])
        self.assertEqual(interaction.followup.send.await_args_list[1].kwargs, {"ephemeral": True})

    async def test_more_explains_the_delivered_read_without_asking_the_coach(self):
        coach_bot.accept(self.guild.id, fresh_reply())
        topic = coach_bot.bot.topics[self.guild.id]
        with patch.object(coach_bot, "coach") as asked, patch.object(coach_bot, "read_live_game") as feed:
            first = await coach_bot.make_answer(self.guild.id, "explain more")
            again = await coach_bot.make_answer(self.guild.id, "keep going")
            self.assertEqual((first.layer, again.layer, topic.layer), (1, 1, 0))   # not delivered: no advance
            self.assertEqual(first, again)
            coach_bot.accept(self.guild.id, first)
            second = await coach_bot.make_answer(self.guild.id, "go on")
            focused = await coach_bot.make_answer(self.guild.id, "why beta")
        asked.assert_not_called()
        feed.assert_not_called()
        self.assertEqual((second.layer, topic.layer), (2, 1))
        self.assertTrue(first.startswith("Game read, continued (live game, as of 3:28): why these two.\n"))
        self.assertIn("**Alpha**", first)
        self.assertIn("Otherwise: **Beta**", first)
        self.assertTrue(first.endswith("Your call."))
        self.assertEqual(first.spoken,
                         "From the 3:28 read: Alpha, or beta. Alpha. Push the wave. Beta. Reset now. Your call.")
        self.assertTrue(focused.spoken.startswith("From the 3:28 read: Before you pick beta or alpha. Beta. "),
                        focused.spoken)

    async def test_an_explanation_is_posted_and_spoken_through_the_usual_path(self):
        coach_bot.accept(self.guild.id, fresh_reply())
        with patch.object(coach_bot, "transcribe_pcm", return_value="Explain more."), \
             patch.object(coach_bot, "coach") as asked, \
             patch.object(coach_bot, "speak_with_refresh", new_callable=AsyncMock, return_value=None) as spoke:
            await coach_bot.process_voice_question(self.guild, 0, "Player", b"pcm", local=True,
                                                   version_at_press=self._press())
        asked.assert_not_called()
        sent = [call.args[0] for call in self.channel.send.await_args_list]
        self.assertEqual(sent[0], "**Player asked in voice:** Explain more")
        self.assertTrue(sent[1].startswith("Game read, continued"))
        self.assertEqual(coach_bot.spoken_script(spoke.await_args.args[3]),
                         "From the 3:28 read: Alpha, or beta. Alpha. Push the wave. Beta. Reset now. Your call.")
        self.assertEqual(coach_bot.bot.topics[self.guild.id].layer, 1)

    async def test_more_with_nothing_to_explain_asks_for_a_fresh_read(self):
        with patch.object(coach_bot, "coach", return_value="Game read (live game): fresh") as asked:
            answer = await coach_bot.make_answer(self.guild.id, "keep going")
        self.assertEqual(answer, "Game read (live game): fresh")
        self.assertEqual(asked.call_args.args[0], "What are our options now?")
        self.assertEqual(asked.call_args.args[0], coach_bot.DEFAULT_QUESTION)
        self.assertEqual((asked.call_args.kwargs["defer_board"], asked.call_args.kwargs["champion_ask"]),
                         (True, True))
        self.assertIs(asked.call_args.kwargs["coordinator_board"], coach_bot.bot.coordinators)
        with patch.object(coach_bot, "coach", return_value="x") as asked:
            await coach_bot.make_answer(self.guild.id, "should I gank top")
        self.assertEqual(asked.call_args.args[0], "should I gank top")

    def test_the_topic_ends_with_the_match_or_with_time(self):
        def stored(read_at=1000.0, at=1000.0, **changes):
            state = coach_bot.bot
            state.topics[self.guild.id] = a_topic(**changes)
            state.topic_read_at[self.guild.id], state.topic_at[self.guild.id] = read_at, at
            return state.topics[self.guild.id]

        with patch.object(coach_bot.time, "monotonic", return_value=1180.0):
            topic = stored()
            self.assertIs(coach_bot.live_topic(self.guild.id), topic)
            stored(match_key=("another", "match"))
            self.assertIsNone(coach_bot.live_topic(self.guild.id))
            self.assertNotIn(self.guild.id, coach_bot.bot.topics)
            self.assertNotIn(self.guild.id, coach_bot.bot.topic_at)
            # A restart with the same ten players keeps the match key; the board's serial tells them apart.
            stored(serial=coach_bot.bot.coordinators.match_serial + 1)
            self.assertIsNone(coach_bot.live_topic(self.guild.id))
            self.assertNotIn(self.guild.id, coach_bot.bot.topics)
        with patch.object(coach_bot.time, "monotonic", return_value=1181.0):
            stored()
            self.assertIsNone(coach_bot.live_topic(self.guild.id))          # 180 seconds idle
            topic = stored(at=1100.0)
            self.assertIs(coach_bot.live_topic(self.guild.id), topic)       # a delivered layer keeps it alive
        with patch.object(coach_bot.time, "monotonic", return_value=1361.0):
            stored(at=1300.0)
            self.assertIsNone(coach_bot.live_topic(self.guild.id))          # 360 seconds after the read
        self.assertIsNone(coach_bot.live_topic(self.guild.id))


if __name__ == "__main__":
    unittest.main()
