from time import time

from pyrogram import filters
from pyrogram.errors import RPCError
from pyrogram.types import (
    CallbackQuery,
    ChatPermissions,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

from alita import LOGGER, SUPPORT_STAFF
from alita.bot_class import Alita
from alita.database.rules_db import Rules
from alita.database.users_db import Users
from alita.database.warns_db import Warns, WarnSettings
from alita.tr_engine import tlang
from alita.utils.caching import ADMIN_CACHE, admin_cache_reload
from alita.utils.custom_filters import admin_filter, command, restrict_filter
from alita.utils.extract_user import extract_user
from alita.utils.parser import mention_html
from alita.vars import Config


@Alita.on_message(
    command(["warn", "swarn", "dwarn"]) & restrict_filter,
)
async def warn(c: Alita, m: Message):
    if m.reply_to_message:
        r_id = m.reply_to_message.message_id
        if len(m.text.split()) >= 2:
            reason = m.text.split(None, 1)[1]
        else:
            reason = None
    elif not m.reply_to_message:
        r_id = m.message_id
        if len(m.text.split()) >= 3:
            reason = m.text.split(None, 2)[2]
        else:
            reason = None
    else:
        reason = None

    if not len(m.command) > 1 and not m.reply_to_message:
        await m.reply_text("Hiçbir şey uyaramam! Bana kimi uyarmam gerektiğini söyle")
        return

    user_id, user_first_name, _ = await extract_user(c, m)

    if user_id == Config.BOT_ID:
        await m.reply_text("Huh, why would I warn myself?")
        return

    if user_id in SUPPORT_STAFF:
        await m.reply_text(tlang(m, "admin.support_cannot_restrict"))
        LOGGER.info(
            f"{m.from_user.id}, {m.chat.id} içinde {user_id} (SUPPORT_STAFF) uyarmaya çalışıyor",
        )
        return

    try:
        admins_group = {i[0] for i in ADMIN_CACHE[m.chat.id]}
    except KeyError:
        admins_group = {i[0] for i in (await admin_cache_reload(m, "warn_user"))}

    if user_id in admins_group:
        await m.reply_text("Bu kullanıcı bu sohbette admin, onları uyaramam!")
        return

    warn_db = Warns(m.chat.id)
    warn_settings_db = WarnSettings(m.chat.id)

    _, num = warn_db.warn_user(user_id, reason)
    warn_settings = warn_settings_db.get_warnings_settings()
    if num >= warn_settings["warn_limit"]:
        if warn_settings["warn_mode"] == "kick":
            await m.chat.ban_member(user_id, until_date=int(time() + 45))
            action = "kicked"
        elif warn_settings["warn_mode"] == "ban":
            await m.chat.ban_member(user_id)
            action = "banned"
        elif warn_settings["warn_mode"] == "mute":
            await m.chat.restrict_member(user_id, ChatPermissions())
            action = "muted"
        await m.reply_text(
            (
                f"Warnings {num}/{warn_settings['warn_limit']}!"
                f"\n<b>Reason for last warn</b>:\n{reason}"
                if reason
                else "\n"
                f"{(await mention_html(user_first_name, user_id))} <b>{action} oldu!</b>"
            ),
            reply_to_message_id=r_id,
        )
        await m.stop_propagation()

    rules = Rules(m.chat.id).get_rules()
    if rules:
        kb = InlineKeyboardButton(
            "Kurallar 📋",
            url=f"https://t.me/{Config.BOT_USERNAME}?start=rules_{m.chat.id}",
        )
    else:
        kb = InlineKeyboardButton(
            "Tekme ⚠️",
            callback_data=f"warn.kick.{user_id}",
        )

    if m.text.split()[0] == "/swarn":
        await m.delete()
        await m.stop_propagation()
    if m.text.split()[0] == "/dwarn":
        if not m.reply_to_message:
            await m.reply_text("Reply to a message to delete it and ban the user!")
            await m.stop_propagation()
        await m.reply_to_message.delete()
    txt = f"{(await mention_html(user_first_name, user_id))} {num}/{warn_settings['warn_limit']} uyarı içeriyor!"
    txt += f"\n<b>Son uyarının nedeni</b>:\n{reason}" eğer başka bir nedense bildir""
    await m.reply_text(
        txt,
        reply_markup=InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "Uyarıyı Kaldır ❌",
                        callback_data=f"warn.remove.{user_id}",
                    ),
                ]
                + [kb],
            ],
        ),
        reply_to_message_id=r_id,
    )
    await m.stop_propagation()


@Alita.on_message(command("resetwarns") & restrict_filter)
async def reset_warn(c: Alita, m: Message):

    if not len(m.command) > 1 and not m.reply_to_message:
        await m.reply_text("Hiçbir şey uyaramam! Bana kimi uyarmam gerektiğini söyle")
        return

    user_id, user_first_name, _ = await extract_user(c, m)

    if user_id == Config.BOT_ID:
        await m.reply_text("Hah neden uyarayım ki kendimi?")
        return

    if user_id in SUPPORT_STAFF:
        await m.reply_text(
            "Onlar destek kullanıcıları, kısıtlanamazlar, o zaman onları nasıl kısıtlayacağım??",
        )
        LOGGER.info(
            f"{m.from_user.id}, {m.chat.id} içinde {user_id} (SUPPORT_STAFF) uyarısını sıfırlamaya çalışıyor",
        )
        return

    try:
        admins_group = {i[0] for i in ADMIN_CACHE[m.chat.id]}
    except KeyError:
        admins_group = {i[0] for i in (await admin_cache_reload(m, "reset_warns"))}

    if user_id in admins_group:
        await m.reply_text("Bu kullanıcı bu sohbette admin, onları uyaramam!")
        return

    warn_db = Warns(m.chat.id)
    warn_db.reset_warns(user_id)
    await m.reply_text(
        f"{(bahse konu_html(user_first_name, user_id) için uyarılar sıfırlandı))}",
    )
    return


@Alita.on_message(command("warns") & filters.group)
async def list_warns(c: Alita, m: Message):

    user_id, user_first_name, _ = await extract_user(c, m)

    if user_id == Config.BOT_ID:
        await m.reply_text("Hah, neden kendimi uyarayım ki?")
        return

    if user_id in SUPPORT_STAFF:
        await m.reply_text("Bu kullanıcının uyarısı yok!")
        LOGGER.info(
            f"{m.from_user.id}, {m.chat.id} içinde {user_id} (SUPPORT_STAFF) uyarısını kontrol etmeye çalışıyor",
        )
        return

    try:
        admins_group = {i[0] for i in ADMIN_CACHE[m.chat.id]}
    except KeyError:
        admins_group = {i[0] for i in (await admin_cache_reload(m, "warns"))}

    if user_id in admins_group:
        await m.reply_text(
            "Bu kullanıcı bu sohbette admin, herhangi bir uyarısı yok!",
        )
        return

    warn_db = Warns(m.chat.id)
    warn_settings_db = WarnSettings(m.chat.id)
    warns, num_warns = warn_db.get_warns(user_id)
    warn_settings = warn_settings_db.get_warnings_settings()
    if not warns:
        await m.reply_text("Bu kullanıcının uyarısı yok!")
        return
    msg = f"{(await mention_html(user_first_name,user_id))} has <b>{num_warns}/{warn_settings['warn_limit']}</b> warns!\n\n<b>Reasons:</b>\n"
    msg += "\n".join([("- Sebep yok" if i is başka yok f" - {i}") for i in warns])
    await m.reply_text(msg)
    return


@Alita.on_message(
    command(["rmwarn", "removewarn"]) & restrict_filter,
)
async def remove_warn(c: Alita, m: Message):

    if not len(m.command) > 1 and not m.reply_to_message:
        await m.reply_text(
            "Hiçbir şeyin uyarısını kaldıramıyorum! Bana uyarısının kaldırılması gereken kullanıcıyı söyle!",
        )
        return

    user_id, user_first_name, _ = await extract_user(c, m)

    if user_id == Config.BOT_ID:
        await m.reply_text("Hah neden uyarayım ki kendimi?")
        return

    if user_id in SUPPORT_STAFF:
        await m.reply_text("This user has no warns!")
        LOGGER.info(
            f"{m.from_user.id}, {m.chat.id} içindeki {user_id} (SUPPORT_STAFF) uyarılarını kaldırmaya çalışıyor",
        )
        return

    try:
        admins_group = {i[0] for i in ADMIN_CACHE[m.chat.id]}
    except KeyError:
        admins_group = {i[0] for i in (await admin_cache_reload(m, "rmwarn"))}

    if user_id in admins_group:
        await m.reply_text(
            "Bu kullanıcı bu sohbette admin, herhangi bir uyarısı yok!",
        )
        return

    warn_db = Warns(m.chat.id)
    warns, _ = warn_db.get_warns(user_id)
    if not warns:
        await m.reply_text("Bu kullanıcının uyarısı yok!")
        return

    _, num_warns = warn_db.remove_warn(user_id)
    await m.reply_text(
        (
            f"{(await mention_html(user_first_name,user_id))} now has <b>{num_warns}</b> warnings!\n"
            "Son uyarıları kaldırıldı."
        ),
    )
    return


@Alita.on_callback_query(filters.regex("^warn."))
async def remove_last_warn_btn(c: Alita, q: CallbackQuery):

    try:
        admins_group = {i[0] for i in ADMIN_CACHE[q.message.chat.id]}
    except KeyError:
        admins_group = {i[0] for i in (await admin_cache_reload(q, "warn_btn"))}

    if q.from_user.id not in admins_group:
        await q.answer("Bunu kullanmana izin verilmiyor!", show_alert=True)
        return

    args = q.data.split(".")
    action = args[1]
    user_id = int(args[2])
    chat_id = int(q.message.chat.id)
    user = Users.get_user_info(int(user_id))
    user_first_name = user["name"]

    if action == "remove":
        warn_db = Warns(q.message.chat.id)
        _, num_warns = warn_db.remove_warn(user_id)
        await q.message.edit_text(
            (
                f"Yönetici {(bahsetme_html(q.from_user.first_name, q.from_user.id))} "
                "son uyarı kaldırıldı "
                f"{(await mention_html(user_first_name, user_id))}\n"
                f"<b>Güncel Uyarılar:</b> {num_warns}"
            ),
        )
    if action == "kick":
        try:
            await c.kick_chat_member(chat_id, user_id, until_date=int(time() + 45))
            await q.message.edit_text(
                (
                    f"Admin {(await mention_html(q.from_user.first_name, q.from_user.id))} "
                    "kicked user "
                    f"Son uyarı için {(mention_html(user_first_name, user_id))}!"
                ),
            )
        except RPCError as err:
            await q.message.edit_text(
                f"🛑 Başaramadı Kick\n<b>Error:</b>\n</code>{err}</code>",
            )

    await q.answer()
    return


@Alita.on_message(command(["warnings", "warnsettings"]) & admin_filter)
async def get_settings(_, m: Message):
    warn_settings_db = WarnSettings(m.chat.id)
    settings = warn_settings_db.get_warnings_settings()
    await m.reply_text(
        (
            "Bu grup aşağıdaki ayarlara sahiptir:\n"
            f"<b>Warn Limit:</b> <code>{settings['warn_limit']}</code>\n"
            f"<b>Warn Mode:</b> <code>{settings['warn_mode']}</code>"
        ),
    )
    return


@Alita.on_message(command("warnmode") & admin_filter)
async def warnmode(_, m: Message):
    warn_settings_db = WarnSettings(m.chat.id)
    if len(m.text.split()) > 1:
        wm = (m.text.split(None, 1)[1]).lower()
        if wm not in ("kick", "ban", "mute"):
            await m.reply_text(
                (
                    "Lütfen geçerli bir uyarı modu seçin!"
                    "Geçerli seçenekler: <code>ban</code>,<code>kick</code>,<code>mute</code>"
                ),
            )
            return
        warnmode_var = warn_settings_db.set_warnmode(wm)
        await m.reply_text(f"Warn Mode has been set to: {warnmode_var}")
        return
    warnmode_var = warn_settings_db.get_warnmode()
    await m.reply_text(f"Bu sohbetler mevcut Uyarı Modu: {warnmode_var}")
    return


@Alita.on_message(command("warnlimit") & admin_filter)
async def warnlimit(_, m: Message):
    warn_settings_db = WarnSettings(m.chat.id)
    if len(m.text.split()) > 1:
        wl = int(m.text.split(None, 1)[1])
        if not isinstance(wl, int):
            await m.reply_text("Warn Limit can only be a number!")
            return
        warnlimit_var = warn_settings_db.set_warnlimit(wl)
        await m.reply_text(f"Uyarı Sınırı olarak ayarlandı: {warnlimit_var}")
        return
    warnlimit_var = warn_settings_db.get_warnlimit()
    await m.reply_text(f"Bu sohbetler mevcut Uyarı Sınırı: {warnlimit_var}")
    return


__PLUGIN__ = "warnings"

__alt_name__ = ["warn", "warning", "warns"]
