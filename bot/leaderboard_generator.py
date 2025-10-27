from typing import List, Dict


def escape_markdown(text: str) -> str:
    """Escape Markdown special characters in text."""
    special_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    for char in special_chars:
        text = text.replace(char, '\\' + char)
    return text


def generate_leaderboard_message(leaderboard_data: List[Dict], chapter: str, total_questions: int) -> str:
    chapter_escaped = escape_markdown(chapter)
    
    if not leaderboard_data:
        return (
            "╭─────────────────────╮\n"
            "│  📊 **LEADERBOARD** │\n"
            "╰─────────────────────╯\n\n"
            "❌ No participants found!\n\n"
            f"Chapter: {chapter_escaped}\n"
            "【~@DrQuizRobot】"
        )
    
    medal_emojis = {
        1: "🥇",
        2: "🥈",
        3: "🥉"
    }
    
    header = (
        "╔═══════════════════════════════╗\n"
        "║   🏆 **QUIZ LEADERBOARD** 🏆   ║\n"
        "╚═══════════════════════════════╝\n\n"
        f"📚 **Chapter:** {chapter_escaped}\n"
        f"📝 **Total Questions:** {total_questions}\n"
        f"👥 **Total Participants:** {len(leaderboard_data)}\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    )
    
    participants_section = ""
    
    for participant in leaderboard_data:
        rank = participant['rank']
        medal = medal_emojis.get(rank, f"#{rank}")
        
        name = escape_markdown(participant['user_name'])
        if len(name) > 15:
            name = name[:12] + "..."
        
        user_id = participant['user_id']
        clickable_name = f"[{name}](tg://user?id={user_id})"
        
        score = participant['total_score']
        attempted = participant['total_attempted']
        correct = participant['correct_answers']
        wrong = participant['wrong_answers']
        unattempted = participant['unattempted']
        time_taken = participant['total_time']
        accuracy = participant['accuracy']
        
        minutes = int(time_taken // 60)
        seconds = int(time_taken % 60)
        time_str = f"{minutes}m {seconds}s" if minutes > 0 else f"{seconds}s"
        
        rank_bar = "━" * min(20, score)
        
        participants_section += f"**{medal} {clickable_name}**\n"
        participants_section += f"├ 💯 Score: **{score}/{total_questions}** ({accuracy:.1f}%)\n"
        participants_section += f"├ ✅ Correct: {correct} │ ❌ Wrong: {wrong} │ ⏭️ Skipped: {unattempted}\n"
        participants_section += f"├ ⏱️ Time: {time_str}\n"
        participants_section += f"└ {'🟢' if accuracy >= 80 else '🟡' if accuracy >= 50 else '🔴'} {rank_bar}\n\n"
    
    footer = (
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "🎯 **Quiz Statistics**\n"
    )
    
    total_correct = sum(p['correct_answers'] for p in leaderboard_data)
    total_wrong = sum(p['wrong_answers'] for p in leaderboard_data)
    total_attempted = sum(p['total_attempted'] for p in leaderboard_data)
    avg_score = sum(p['total_score'] for p in leaderboard_data) / len(leaderboard_data)
    avg_accuracy = sum(p['accuracy'] for p in leaderboard_data) / len(leaderboard_data)
    
    stats = (
        f"├ Average Score: {avg_score:.1f}/{total_questions}\n"
        f"├ Average Accuracy: {avg_accuracy:.1f}%\n"
        f"├ Total Attempts: {total_attempted}\n"
        f"├ Total Correct: {total_correct}\n"
        f"└ Total Wrong: {total_wrong}\n\n"
    )
    
    help_section = (
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "💡 **Need Explanation?**\n"
        "Reply to any quiz question with `/explain`\n"
        "to get detailed AI-powered explanation!\n\n"
    )
    
    closing = (
        "╭─────────────────────────────╮\n"
        "│  🌟 Thank you for playing! 🌟  │\n"
        "╰─────────────────────────────╯\n\n"
        "【~@DrQuizRobot】"
    )
    
    return header + participants_section + footer + stats + help_section + closing


def generate_quiz_complete_message(total_questions: int) -> str:
    return (
        "╔═══════════════════════════════╗\n"
        "║    ✅ **QUIZ COMPLETED!** ✅    ║\n"
        "╚═══════════════════════════════╝\n\n"
        f"📝 All {total_questions} questions have been answered!\n"
        "⏳ Calculating final scores...\n\n"
        "🏆 Leaderboard coming up! 🏆\n\n"
        "【~@DrQuizRobot】"
    )
