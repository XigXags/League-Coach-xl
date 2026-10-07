"""One real Jev output-check smoke test on synthetic evidence; no generative LLM call."""
import asyncio
from model_pipeline import judge

async def main():
    brief = {"player_question": "What are our options?", "evidence": {
        "game": {"game_time_seconds": 120, "active_level": 3},
        "scoreboard_capture": {"ocr_text": "Ashe 30 CS", "reliability": "unverified OCR"}},
        "prepared_options": [{"play": "Keep farming"}, {"play": "Reset and buy"}],
        "prepared_spoken": "Keep farming. Or reset and buy."}
    checked = await judge("Keep farming your own side. Or reset and buy before the next clear.",
                          brief, {"model": "jev-1.13.0"}, 5)
    print("Jev guard envelope validated:", checked["model"], len(checked["answers"]), "checks")

if __name__ == "__main__":
    asyncio.run(main())
