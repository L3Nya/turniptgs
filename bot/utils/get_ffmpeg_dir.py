from ..constants import WORK_DIR


def get_dir(sticker_id, user_id, size):
    return WORK_DIR / (sticker_id + str(user_id)) / size
