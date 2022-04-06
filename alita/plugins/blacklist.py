from html import escape

from pyrogram import filters
from pyrogram.types import CallbackQuery, Message

from alita import LOGGER
from alita.bot_class import Alita
from alita.database.blacklist_db import Blacklist
from alita.tr_engine import tlang
from alita.utils.custom_filters import command, owner_filter, restrict_filter
from alita.utils.kbhelpers import ikb


@Alita.on_message(command("blacklist") & filters.group)
async def view_blacklist(_, m: Message):
    db = Blacklist(m.chat.id)

    LOGGER.info(f"{m.from_user.id} checking blacklists in {m.chat.id}")

    chat_title = m.chat.title
    blacklists_chat = (tlang(m, "blacklist.curr_blacklist_initial")).format(
        chat_title=chat_title,
    )
    all_blacklisted = db.get_blacklists()

    if not all_blacklisted:
        await m.reply_text(
            (tlang(m, "blacklist.no_blacklist")).format(
                chat_title=chat_title,
            ),
        )
        return

    blacklists_chat += "\n".join(
        f" • <code>{escape(i)}</code>" for i in all_blacklisted
    )

    await m.reply_text(blacklists_chat)
    return


@Alita.on_message(command("addblacklist") & restrict_filter)
async def add_blacklist(_, m: Message):
    db = Blacklist(m.chat.id)

    if len(m.text.split()) < 2:
        await m.reply_text(tlang(m, "general.check_help"))
        return

    bl_words = ((m.text.split(None, 1)[1]).lower()).split()
    all_blacklisted = db.get_blacklists()
    already_added_words, rep_text = [], ""

    for bl_word in bl_words:
        if bl_word in all_blacklisted:
            already_added_words.append(bl_word)
            continue
        db.add_blacklist(bl_word)

    if already_added_words:
        rep_text = (
            ", ".join([f"<code>{i}</code>" for i in bl_words])
            + " zaten kara listeye eklendi, atlandı!"
        )
    LOGGER.info(f"{m.from_user.id}, {m.chat.id} içinde yeni kara listeler ({bl_words}) ekledi")
    await m.reply_text(
        (tlang(m, "blacklist.added_blacklist")).format(
            trigger=", ".join(f"<code>{i}</code>" for i in bl_words),
        )
        + (f"\n{rep_text}" if rep_text else ""),
    )

    await m.stop_propagation()


@Alita.on_message(
    command(["blwarning", "blreason", "blacklistreason"]) & restrict_filter,
)
async def blacklistreason(_, m: Message):
    db = Blacklist(m.chat.id)

    if len(m.text.split()) == 1:
        curr = db.get_reason()
        await m.reply_text(
            f"The current reason for blacklists warn is:\n<code>{curr}</code>",
        )
    else:
        reason = m.text.split(None, 1)[1]
        db.set_reason(reason)
        await m.reply_text(
            f"Kara liste uyarısının güncellenmiş nedeni:\n<code>{reason}</code>",
        )
    return


@Alita.on_message(
    command(["rmblacklist", "unblacklist"]) & restrict_filter,
)
async def rm_blacklist(_, m: Message):
    db = Blacklist(m.chat.id)

    if len(m.text.split()) < 2:
        await m.reply_text(tlang(m, "general.check_help"))
        return

    chat_bl = db.get_blacklists()
    non_found_words, rep_text = [], ""
    bl_words = ((m.text.split(None, 1)[1]).lower()).split()

    for bl_word in bl_words:
        if bl_word not in chat_bl:
            non_found_words.append(bl_word)
            continue
        db.remove_blacklist(bl_word)

    if non_found_words == bl_words:
        return await m.reply_text("Kara listeler bulunamadı!")

    if non_found_words:
        rep_text = (
            "Bulunamadı " + ", ".join(f"<code>{i}</code>" for i in non_found_words)
        ) + " in blcklisted words, skipped them."

    LOGGER.info(f"{m.from_user.id}, {m.chat.id} içeriğindeki kara listeleri ({bl_words}) kaldırma")
    await m.reply_text(
        (tlang(m, "blacklist.rm_blacklist")).format(
            bl_words=", ".join(f"<code>{i}</code>" for i in bl_words),
        )
        + (f"\n{rep_text}" eğer rep_text else ""),
    )

    await m.stop_propagation()


@Alita.on_message(
    command(["blaction", "blacklistaction", "blacklistmode"]) & restrict_filter,
)
async def set_bl_action(_, m: Message):
    db = Blacklist(m.chat.id)

    if len(m.text.split()) == 2:
        action = m.text.split(None, 1)[1]
        valid_actions = ("ban", "kick", "mute", "warn", "none")
        if action not in valid_actions:
            await m.reply_text(
                (
                    "Choose a valid blacklist action from "
                    + ", ".join(f"<code>{i}</code>" for i in valid_actions)
                ),
            )

            return
        db.set_action(action)
        LOGGER.info(
            f"{m.from_user.id}, {m.chat.id}'de kara liste eylemini '{action}' olarak ayarla",
        )
        await m.reply_text(
            (tlang(m, "blacklist.action_set")).format(action=action),
        )
    elif len(m.text.split()) == 1:
        action = db.get_action()
        LOGGER.info(f"{m.from_user.id}, {m.chat.id} içindeki kara liste işlemini kontrol ediyor")
        await m.reply_text(
            (tlang(m, "blacklist.action_get")).format(action=action),
        )
    else:
        await m.reply_text(tlang(m, "general.check_help"))

    return


@Alita.on_message(
    command("rmallblacklist") & owner_filter,
)
async def rm_allblacklist(_, m: Message):
    db = Blacklist(m.chat.id)

    all_bls = db.get_blacklists()
    if not all_bls:
        await m.reply_text("No notes are blacklists in this chat")
        return

    await m.reply_text(
        "Are you sure you want to clear all blacklists?",
        reply_markup=ikb(
            [[("⚠️ Onaylama", "rm_allblacklist"), ("❌ İPTAL", "close_admin")]],
        ),
    )
    return


@Alita.on_callback_query(filters.regex("^rm_allblacklist$"))
async def rm_allbl_callback(_, q: CallbackQuery):
    user_id = q.from_user.id
    db = Blacklist(q.message.chat.id)
    user_status = (await q.message.chat.get_member(user_id)).status
    if user_status not in {"creator", "administrator"}:
        await q.answer(
            "Yönetici bile değilsin, bu patlayıcı şeyi deneme!",
            show_alert=True,
        )
        return
    if user_status != "creator":
        await q.answer(
            "Sen sadece bir yöneticisin, sahip değil\sınırlarında kal!",
            show_alert=True,
        )
        return
    db.rm_all_blacklist()
    await q.message.delete()
    LOGGER.info(f"{user_id}, {q.message.chat.id} içindeki tüm kara listeleri kaldırdı")
    await q.answer("Tüm Kara Listeler Temizlendi!", show_alert=True)
    return


__PLUGIN__ = "blacklist"

__alt_name__ = ["blacklists", "blaction"]
