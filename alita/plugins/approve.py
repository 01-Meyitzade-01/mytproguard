from pyrogram import filters
from pyrogram.errors import PeerIdInvalid, RPCError, UserNotParticipant
from pyrogram.types import CallbackQuery, ChatPermissions, Message

from alita import LOGGER, SUPPORT_GROUP
from alita.bot_class import Alita
from alita.database.approve_db import Approve
from alita.utils.custom_filters import admin_filter, command, owner_filter
from alita.utils.extract_user import extract_user
from alita.utils.kbhelpers import ikb
from alita.utils.parser import mention_html


@Alita.on_message(command("approve") & admin_filter)
async def approve_user(c: Alita, m: Message):
    db = Approve(m.chat.id)

    chat_title = m.chat.title

    try:
        user_id, user_first_name, _ = await extract_user(c, m)
    except Exception:
        return

    if not user_id:
        await m.reply_text(
            "Kimden bahsettiğini bilmiyorum, bir kullanıcı belirtmen gerekecek!",
        )
        return
    try:
        member = await m.chat.get_member(user_id)
    except UserNotParticipant:
        await m.reply_text("Bu kullanıcı bu sohbette değil!")
        return

    except RPCError as ef:
        await m.reply_text(
            f"<b>Hata</b>: <code>{ef}</code>\nBunu @{SUPPORT_GROUP} adresine bildirin",
        )
        return
    if member.status in ("administrator", "creator"):
        await m.reply_text(
            "Kullanıcı zaten yönetici - kara listeler ve kilitler zaten onlar için geçerli değil.",
        )
        return
    already_approved = db.check_approve(user_id)
    if already_approved:
        await m.reply_text(
            f"{(ait söz_html(user_first_name, user_id))}, {chat_title}'da zaten onaylandı",
        )
        return
    db.add_approve(user_id, user_first_name)
    LOGGER.info(f"{user_id} approved by {m.from_user.id} in {m.chat.id}")

    # Allow all permissions
    try:
        await m.chat.unban_member(user_id=user_id)
    except RPCError as g:
        await m.reply_text(f"Error: {g}")
        return
    await m.reply_text(
        (
            f"{(await mention_html(user_first_name, user_id))} has been approved in {chat_title}!\n"
            "Artık kara listeler, kilitler ve antisel tarafından yok sayılacaklar!"
        ),
    )
    return


@Alita.on_message(
    command(["disapprove", "unapprove"]) & admin_filter,
)
async def disapprove_user(c: Alita, m: Message):
    db = Approve(m.chat.id)

    chat_title = m.chat.title
    try:
        user_id, user_first_name, _ = await extract_user(c, m)
    except Exception:
        return
    already_approved = db.check_approve(user_id)
    if not user_id:
        await m.reply_text(
            "Kimden bahsettiğini bilmiyorum, bir kullanıcı belirtmen gerekecek!",
        )
        return
    try:
        member = await m.chat.get_member(user_id)
    except UserNotParticipant:
        if already_approved:  # If user is approved and not in chat, unapprove them.
            db.remove_approve(user_id)
            LOGGER.info(f"{user_id}, {m.chat.id} içinde UserNotParticipant olarak onaylanmadı")
        await m.reply_text("This user is not in this chat, unapproved them.")
        return
    except RPCError as ef:
        await m.reply_text(
            f"<b>Error</b>: <code>{ef}</code>\nReport it to @{SUPPORT_GROUP}",
        )
        return

    if member.status in ("administrator", "creator"):
        await m.reply_text("Bu kullanıcı bir yöneticidir, reddedilemez.")
        return

    if not already_approved:
        await m.reply_text(
            f"{(await mention_html(user_first_name, user_id))} isn't approved yet!",
        )
        return

    db.remove_approve(user_id)
    LOGGER.info(f"{user_id}, {m.chat.id} içinde {m.from_user.id} tarafından onaylanmadı")

    # Set permission same as of current user by fetching them from chat!
    await m.chat.restrict_member(
        user_id=user_id,
        permissions=m.chat.permissions,
    )

    await m.reply_text(
        f"{(aitbahis_html(user_first_name, user_id))} artık {chat_title}'da onaylanmıyor.",
    )
    return


@Alita.on_message(command("approved") & admin_filter)
async def check_approved(_, m: Message):
    db = Approve(m.chat.id)

    chat = m.chat
    chat_title = chat.title
    msg = "The following users are approved:\n"
    approved_people = db.list_approved()

    if not approved_people:
        await m.reply_text(f"{chat_title}'da hiçbir kullanıcı onaylanmadı.")
        return

    for user_id, user_name in approved_people.items():
        try:
            await chat.get_member(user_id)  # Check if user is in chat or not
        except UserNotParticipant:
            db.remove_approve(user_id)
            continue
        except PeerIdInvalid:
            pass
        msg += f"- `{user_id}`: {user_name}\n"
    await m.reply_text(msg)
    LOGGER.info(f"{m.from_user.id}, {m.chat.id}'deki onaylı kullanıcıları kontrol ediyor")
    return


@Alita.on_message(command("approval") & filters.group)
async def check_approval(c: Alita, m: Message):
    db = Approve(m.chat.id)

    try:
        user_id, user_first_name, _ = await extract_user(c, m)
    except Exception:
        return
    check_approve = db.check_approve(user_id)
    LOGGER.info(f"{m.from_user.id}, {m.chat.id}'de {user_id} kullanıcı onayını kontrol ediyor")

    if not user_id:
        await m.reply_text(
            "Kimden bahsettiğini bilmiyorum, bir kullanıcı belirtmen gerekecek!",
        )
        return
    if check_approve:
        await m.reply_text(
            f"{(awaitbahis_html(user_first_name, user_id))} onaylanmış bir kullanıcıdır. Kilitler, sel önleme ve kara listeler bunlara uygulanmaz.",
        )
    else:
        await m.reply_text(
            f"{(await mention_html(user_first_name, user_id))} onaylı bir kullanıcı değil. Normal komutlardan etkilenirler.",
        )
    return


@Alita.on_message(
    command("unapproveall") & filters.group & owner_filter,
)
async def unapproveall_users(_, m: Message):
    db = Approve(m.chat.id)

    all_approved = db.list_approved()
    if not all_approved:
        await m.reply_text("Bu sohbette kimse onaylanmadı.")
        return

    await m.reply_text(
        "Bu sohbette onaylanan herkesi kaldırmak istediğinizden emin misiniz??",
        reply_markup=ikb(
            [[("⚠️ Onaylama", "unapprove_all"), ("❌ İptal", "close_admin")]],
        ),
    )
    return


@Alita.on_callback_query(filters.regex("^unapprove_all$"))
async def unapproveall_callback(_, q: CallbackQuery):
    user_id = q.from_user.id
    db = Approve(q.message.chat.id)
    approved_people = db.list_approved()
    user_status = (await q.message.chat.get_member(user_id)).status
    if user_status not in {"creator", "administrator"}:
        await q.answer(
            "Yönetici bile değilsin, bu patlayıcı şeyi deneme!",
            show_alert=True,
        )
        return
    if user_status != "creator":
        await q.answer(
            "Sahip değil, bir yöneticisin\nSınırlarında kal!",
            show_alert=True,
        )
        return
    db.unapprove_all()
    for i in approved_people:
        await q.message.chat.restrict_member(
            user_id=i[0],
            permissions=q.message.chat.permissions,
        )
    await q.message.delete()
    LOGGER.info(f"{user_id}, {q.message.chat.id} içindeki tüm kullanıcıları onaylamadı")
    await q.answer("Tüm kullanıcılar onaylanmadı!", show_alert=True)
    return


__PLUGIN__ = "approve"

_DISABLE_CMDS_ = ["approval"]

__alt_name__ = ["approved"]
