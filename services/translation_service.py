import os
import json
import logging


class TranslationService:
    _instance = None
    _strings = {}
    _current_language = "en"

    VIETNAMESE = {
        # Main window
        "app.title": "Engraver Note App",
        "menu.file": "Tệp",
        "menu.file.new_text": "Tạo Text Note",
        "menu.file.new_checklist": "Tạo Checklist",
        "menu.file.save": "Lưu Ghi Chú",
        "menu.file.delete": "Xóa Ghi Chú",
        "menu.file.export_md": "Xuất Markdown",
        "menu.file.export_pdf": "Xuất PDF",
        "menu.file.export_media_zip": "Xuất media ZIP có mật khẩu",
        "menu.file.open_media_zip": "Mở / giải nén media ZIP",
        "menu.edit": "Chỉnh sửa",
        "menu.edit.undo": "Hoàn tác",
        "menu.edit.redo": "Làm lại",
        "menu.view": "Xem",
        "menu.view.calendar": "Lịch biểu",
        "menu.options": "Tùy chọn",
        "menu.options.lock": "Khóa / Gỡ khóa Ghi Chú",
        "menu.options.appearance": "Chế độ",
        "menu.options.theme": "Chủ đề màu",
        "menu.options.language": "Ngôn ngữ",
        "menu.options.language.en": "Tiếng Anh",
        "menu.options.language.vi": "Tiếng Việt",

        # Sidebar
        "sidebar.logo": "Engraver",
        "sidebar.search_placeholder": "Tìm kiếm...",
        "sidebar.note_list": "Danh sách Ghi chú",
        "sidebar.deleted_list": "Bị xoá gần đây",
        "sidebar.no_deleted": "Không có mục đã xóa",
        "sidebar.no_title": "Không có tiêu đề",
        "sidebar.new_folder": "Thư mục mới",
        "sidebar.all_notes": "Tất cả ghi chú",
        "msg.new_folder_title": "Thư mục mới",
        "msg.new_folder_prompt": "Nhập tên thư mục cần tạo:",
        "msg.folder_empty": "Tên thư mục không được để trống!",
        "msg.create_in_folder_title": "Tạo ghi chú mới",
        "msg.create_in_folder_prompt": "Tạo ghi chú trong thư mục '{0}':",
        "msg.btn_text_note": "Text Note (T)",
        "msg.btn_checklist": "Checklist (C)",

        # Editor
        "editor.title_placeholder": "Nhập tiêu đề...",
        "editor.bold": "B",
        "editor.italic": "I",
        "editor.underline": "U",
        "editor.font": "Phông chữ",
        "editor.size": "Cỡ chữ",
        "editor.text_color": "Màu chữ",
        "editor.highlight": "Highlight",
        "editor.zoom": "Phóng to / Thu nhỏ",
        "editor.insert_media": "📎 Media",
        "editor.choose_media": "Chọn ảnh, âm thanh hoặc video",
        "editor.open_media": "Mở",
        "editor.reminder_label": "Nhắc lúc",
        "editor.deadline_label": "Hạn chót",
        "editor.date_picker_reminder": "Chọn thời gian nhắc",
        "editor.date_picker_deadline": "Chọn thời gian hạn chót",
        "editor.checklist_placeholder": "Thêm công việc mới...",
        "editor.checklist_add": "Thêm",
        "editor.reminder_placeholder": "YYYY-MM-DD HH:MM",
        "editor.deadline_placeholder": "YYYY-MM-DD HH:MM",
        "editor.content_search_placeholder": "Tìm trong ghi chú...",

        # Messages
        "msg.save_success": "Đã lưu ghi chú.",
        "msg.save_error": "Lỗi",
        "msg.title_empty": "Tiêu đề không được trống!",
        "msg.time_error": "Lỗi thời gian",
        "msg.time_format_error": "Sai định dạng thời gian. Vui lòng dùng YYYY-MM-DD HH:MM, ví dụ 2026-07-01 20:30.",
        "msg.delete_confirm": "Xác nhận",
        "msg.delete_confirm_text": "Xóa ghi chú?",
        "msg.permanent_delete_confirm": "Xác nhận",
        "msg.permanent_delete_confirm_text": "Xóa vĩnh viễn ghi chú này? Không thể khôi phục lại.",
        "msg.lock_title": "Ghi chú đã khóa",
        "msg.lock_prompt": "Nhập mật khẩu để mở ghi chú:",
        "msg.lock_wrong": "Sai mật khẩu",
        "msg.lock_wrong_text": "Không thể mở ghi chú vì mật khẩu không đúng.",
        "msg.lock_first": "Lỗi",
        "msg.lock_first_text": "Hãy lưu ghi chú trước khi đặt mật khẩu.",
        "msg.lock_not_found": "Lỗi",
        "msg.lock_not_found_text": "Không tìm thấy ghi chú hiện tại.",
        "msg.lock_enter_current": "Nhập mật khẩu hiện tại:",
        "msg.lock_unlock_fail": "Sai mật khẩu",
        "msg.lock_unlock_fail_text": "Không thể gỡ khóa vì mật khẩu không đúng.",
        "msg.lock_unlock_success": "Thành công",
        "msg.lock_unlock_success_text": "Đã gỡ khóa ghi chú.",
        "msg.lock_new_password": "Nhập mật khẩu mới:",
        "msg.lock_weak": "Mật khẩu yếu",
        "msg.lock_weak_text": "Mật khẩu nên có ít nhất 4 ký tự.",
        "msg.lock_confirm": "Xác nhận mật khẩu",
        "msg.lock_confirm_text": "Nhập lại mật khẩu:",
        "msg.lock_mismatch": "Không khớp",
        "msg.lock_mismatch_text": "Hai lần nhập mật khẩu không giống nhau.",
        "msg.lock_success": "Thành công",
        "msg.lock_success_text": "Đã khóa ghi chú. Lần mở sau sẽ cần nhập mật khẩu.",
        "msg.export_success": "Thành công",
        "msg.export_no_note": "Lỗi",
        "msg.export_no_note_text": "Chọn ghi chú để xuất!",
        "msg.export_success_text": "Đã xuất tại: {path}",
        "msg.export_pdf_error": "Lỗi PDF",
        "msg.export_pdf_error_text": "Không xuất được PDF: {error}",
        "msg.media_error": "Lỗi media",
        "msg.media_zip_password_title": "Mật khẩu ZIP media",
        "msg.media_zip_password_prompt": "Nhập mật khẩu cho file ZIP (ít nhất 4 ký tự):",
        "msg.media_zip_password_confirm": "Nhập lại mật khẩu ZIP:",
        "msg.media_zip_password_short": "Mật khẩu ZIP phải có ít nhất 4 ký tự.",
        "msg.media_zip_password_mismatch": "Hai lần nhập mật khẩu không giống nhau.",
        "msg.media_zip_success": "Đã đóng gói {count} file media tại: {path}",
        "msg.media_zip_error": "Lỗi ZIP media",
        "msg.media_zip_open_title": "Chọn file media ZIP để mở",
        "msg.media_zip_open_password": "Nhập mật khẩu của file ZIP:",
        "msg.media_zip_destination": "Chọn thư mục giải nén",
        "msg.media_zip_wrong_password": "Mật khẩu không đúng hoặc file ZIP đã bị hỏng.",
        "msg.media_zip_extract_success": "Đã giải nén {count} file tại: {path}",

        # Reminder / Deadline notifications
        "reminder.title": "🔔 Nhắc nhở ghi chú",
        "reminder.text": "Đã đến giờ nhắc cho ghi chú: {title}",
        "deadline.title": "📌 Hạn chót ghi chú",
        "deadline.text": "Đã đến hạn chót (deadline) cho ghi chú: {title}",

        # Calendar
        "calendar.title": "Lịch biểu ghi chú",
        "calendar.prev": "← Tháng trước",
        "calendar.next": "Tháng sau →",
        "calendar.hint": "🔔 = Reminder, 📌 = Deadline. Bấm vào ghi chú trong lịch để mở.",
        "calendar.extra": "+{count} mục khác",
        "calendar.no_title": "Không có tiêu đề",
        "calendar.month_label": "Tháng {0:02d}/{1}",

        # Date Picker
        "datepicker.title": "Chọn thời gian",
        "datepicker.hour": "Giờ:",
        "datepicker.minute": "Phút:",
        "datepicker.set_now": "Đặt về hiện tại",
        "datepicker.apply": "Áp dụng",
        "datepicker.cancel": "Hủy",
        "datepicker.time_error": "Lỗi thời gian",
        "datepicker.time_error_text": "Vui lòng chọn ngày, giờ và phút hợp lệ.",
        "datepicker.month_label": "Tháng {0:02d}/{1}",

        # Color Picker
        "colorpicker.current_color": "Màu hiện tại:",
        "colorpicker.presets": "Bảng màu có sẵn:",
        "colorpicker.hex_label": "Mã Hex:",
        "colorpicker.cancel": "Hủy",
        "colorpicker.apply": "Áp dụng",

        # Weekdays
        "weekday.0": "T2",
        "weekday.1": "T3",
        "weekday.2": "T4",
        "weekday.3": "T5",
        "weekday.4": "T6",
        "weekday.5": "T7",
        "weekday.6": "CN",

        # Months
        "month.1": "Tháng 1",
        "month.2": "Tháng 2",
        "month.3": "Tháng 3",
        "month.4": "Tháng 4",
        "month.5": "Tháng 5",
        "month.6": "Tháng 6",
        "month.7": "Tháng 7",
        "month.8": "Tháng 8",
        "month.9": "Tháng 9",
        "month.10": "Tháng 10",
        "month.11": "Tháng 11",
        "month.12": "Tháng 12",
    }

    ENGLISH = {
        # Main window
        "app.title": "Engraver Note App",
        "menu.file": "File",
        "menu.file.new_text": "New Text Note",
        "menu.file.new_checklist": "New Checklist",
        "menu.file.save": "Save Note",
        "menu.file.delete": "Delete Note",
        "menu.file.export_md": "Export Markdown",
        "menu.file.export_pdf": "Export PDF",
        "menu.file.export_media_zip": "Export password-protected media ZIP",
        "menu.file.open_media_zip": "Open / extract media ZIP",
        "menu.edit": "Edit",
        "menu.edit.undo": "Undo",
        "menu.edit.redo": "Redo",
        "menu.view": "View",
        "menu.view.calendar": "Calendar",
        "menu.options": "Options",
        "menu.options.lock": "Lock / Unlock Note",
        "menu.options.appearance": "Appearance",
        "menu.options.theme": "Color Theme",
        "menu.options.language": "Language",
        "menu.options.language.en": "English",
        "menu.options.language.vi": "Vietnamese",

        # Sidebar
        "sidebar.logo": "Engraver",
        "sidebar.search_placeholder": "Search...",
        "sidebar.note_list": "Notes",
        "sidebar.deleted_list": "Recently Deleted",
        "sidebar.no_deleted": "No deleted items",
        "sidebar.no_title": "No title",
        "sidebar.new_folder": "New Folder",
        "sidebar.all_notes": "All Notes",
        "msg.new_folder_title": "New Folder",
        "msg.new_folder_prompt": "Enter new folder name:",
        "msg.folder_empty": "Folder name cannot be empty!",
        "msg.create_in_folder_title": "New Note",
        "msg.create_in_folder_prompt": "Create note in folder '{0}':",
        "msg.btn_text_note": "Text Note (T)",
        "msg.btn_checklist": "Checklist (C)",   

        # Editor
        "editor.title_placeholder": "Enter title...",
        "editor.bold": "B",
        "editor.italic": "I",
        "editor.underline": "U",
        "editor.font": "Font",
        "editor.size": "Size",
        "editor.text_color": "Text Color",
        "editor.highlight": "Highlight",
        "editor.zoom": "Zoom",
        "editor.insert_media": "📎 Media",
        "editor.choose_media": "Choose images, audio, or video",
        "editor.open_media": "Open",
        "editor.reminder_label": "🔔 Remind at",
        "editor.deadline_label": "📌 Deadline",
        "editor.date_picker_reminder": "Pick reminder time",
        "editor.date_picker_deadline": "Pick deadline",
        "editor.checklist_placeholder": "Add new task...",
        "editor.checklist_add": "Add",
        "editor.reminder_placeholder": "YYYY-MM-DD HH:MM",
        "editor.deadline_placeholder": "YYYY-MM-DD HH:MM",
        "editor.content_search_placeholder": "Search in note...",

        # Messages
        "msg.save_success": "Note saved successfully.",
        "msg.save_error": "Error",
        "msg.title_empty": "Title cannot be empty!",
        "msg.time_error": "Time Error",
        "msg.time_format_error": "Invalid time format. Please use YYYY-MM-DD HH:MM, e.g. 2026-07-01 20:30.",
        "msg.delete_confirm": "Confirm",
        "msg.delete_confirm_text": "Delete this note?",
        "msg.permanent_delete_confirm": "Confirm",
        "msg.permanent_delete_confirm_text": "Permanently delete this note? This cannot be undone.",
        "msg.lock_title": "Locked Note",
        "msg.lock_prompt": "Enter password to unlock:",
        "msg.lock_wrong": "Wrong Password",
        "msg.lock_wrong_text": "Cannot open note because the password is incorrect.",
        "msg.lock_first": "Error",
        "msg.lock_first_text": "Please save the note before setting a password.",
        "msg.lock_not_found": "Error",
        "msg.lock_not_found_text": "Could not find the current note.",
        "msg.lock_enter_current": "Enter current password:",
        "msg.lock_unlock_fail": "Wrong Password",
        "msg.lock_unlock_fail_text": "Cannot unlock because the password is incorrect.",
        "msg.lock_unlock_success": "Success",
        "msg.lock_unlock_success_text": "Note unlocked successfully.",
        "msg.lock_new_password": "Enter new password:",
        "msg.lock_weak": "Weak Password",
        "msg.lock_weak_text": "Password should be at least 4 characters.",
        "msg.lock_confirm": "Confirm Password",
        "msg.lock_confirm_text": "Re-enter password:",
        "msg.lock_mismatch": "Mismatch",
        "msg.lock_mismatch_text": "The two passwords do not match.",
        "msg.lock_success": "Success",
        "msg.lock_success_text": "Note locked. Next time you open it, you'll need the password.",
        "msg.export_success": "Success",
        "msg.export_no_note": "Error",
        "msg.export_no_note_text": "Select a note to export!",
        "msg.export_success_text": "Exported to: {path}",
        "msg.export_pdf_error": "PDF Error",
        "msg.export_pdf_error_text": "Could not export PDF: {error}",
        "msg.media_error": "Media Error",
        "msg.media_zip_password_title": "Media ZIP password",
        "msg.media_zip_password_prompt": "Enter a ZIP password (at least 4 characters):",
        "msg.media_zip_password_confirm": "Re-enter the ZIP password:",
        "msg.media_zip_password_short": "The ZIP password must be at least 4 characters.",
        "msg.media_zip_password_mismatch": "The two passwords do not match.",
        "msg.media_zip_success": "Packed {count} media file(s) at: {path}",
        "msg.media_zip_error": "Media ZIP Error",
        "msg.media_zip_open_title": "Choose a media ZIP to open",
        "msg.media_zip_open_password": "Enter the ZIP password:",
        "msg.media_zip_destination": "Choose an extraction folder",
        "msg.media_zip_wrong_password": "The password is incorrect or the ZIP file is damaged.",
        "msg.media_zip_extract_success": "Extracted {count} file(s) to: {path}",

        # Reminder / Deadline notifications
        "reminder.title": "🔔 Note Reminder",
        "reminder.text": "Time to remind about note: {title}",
        "deadline.title": "📌 Note Deadline",
        "deadline.text": "Deadline has arrived for note: {title}",

        # Calendar
        "calendar.title": "Calendar View",
        "calendar.prev": "← Previous Month",
        "calendar.next": "Next Month →",
        "calendar.hint": "🔔 = Reminder, 📌 = Deadline. Click a note in the calendar to open it.",
        "calendar.extra": "+{count} more items",
        "calendar.no_title": "No title",
        "calendar.month_label": "{0:02d}/{1}",

        # Date Picker
        "datepicker.title": "Pick Date & Time",
        "datepicker.hour": "Hour:",
        "datepicker.minute": "Minute:",
        "datepicker.set_now": "Set to Now",
        "datepicker.apply": "Apply",
        "datepicker.cancel": "Cancel",
        "datepicker.time_error": "Time Error",
        "datepicker.time_error_text": "Please select a valid date, hour and minute.",
        "datepicker.month_label": "{0:02d}/{1}",

        # Color Picker
        "colorpicker.current_color": "Current Color:",
        "colorpicker.presets": "Preset Colors:",
        "colorpicker.hex_label": "Hex Code:",
        "colorpicker.cancel": "Cancel",
        "colorpicker.apply": "Apply",

        # Weekdays
        "weekday.0": "Mon",
        "weekday.1": "Tue",
        "weekday.2": "Wed",
        "weekday.3": "Thu",
        "weekday.4": "Fri",
        "weekday.5": "Sat",
        "weekday.6": "Sun",

        # Months
        "month.1": "January",
        "month.2": "February",
        "month.3": "March",
        "month.4": "April",
        "month.5": "May",
        "month.6": "June",
        "month.7": "July",
        "month.8": "August",
        "month.9": "September",
        "month.10": "October",
        "month.11": "November",
        "month.12": "December",
    }

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(TranslationService, cls).__new__(cls)
            cls._instance._strings = {}
            cls._instance._current_language = "en"
        return cls._instance

    @classmethod
    def set_language(cls, lang_code):
        instance = cls()
        instance._current_language = lang_code
        if lang_code == "vi":
            instance._strings = cls.VIETNAMESE
        else:
            instance._strings = cls.ENGLISH

    @classmethod
    def get_language(cls):
        instance = cls()
        return instance._current_language

    @classmethod
    def get(cls, key, *args, **kwargs):
        """Get translated string by key, with optional format arguments."""
        instance = cls()
        value = instance._strings.get(key, key)
        if args or kwargs:
            try:
                if args:
                    value = value.format(*args)
                else:
                    value = value.format(**kwargs)
            except (KeyError, IndexError):
                pass
        return value

    @classmethod
    def weekdays(cls):
        """Return list of weekday names for the current language."""
        return [cls.get(f"weekday.{i}") for i in range(7)]

    @classmethod
    def month_name(cls, month_num):
        """Return month name for the current language."""
        return cls.get(f"month.{month_num}")

    @classmethod
    def get_available_languages(cls):
        return [
            {"code": "en", "name": cls.ENGLISH["menu.options.language.en"]},
            {"code": "vi", "name": cls.VIETNAMESE["menu.options.language.vi"]},
        ]


# Initialize with English by default
TranslationService.set_language("en")
