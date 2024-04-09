import os


def create_folder(
    folder_name: str, mode: int = 0o750, change_mode: bool = True
) -> None:
    folder_path = os.path.normcase("./" + folder_name)

    if not os.path.isdir(folder_path):
        try:
            os.mkdir(folder_path, mode=mode)
        except:
            # This shoudln't ever be reached, as it would imply that the folder doesn't exist, but the script also is unable to create it. Could possibly be missing read permissions if the scripts catches this exception
            raise Exception(f"The folder {folder_name} couldn't be created, exiting")
    elif change_mode:
        try:
            os.chmod(folder_path, mode)
        except:
            raise Exception(
                f"Failed to set the 750 permissions on {folder_name}, either remove the folder or set the right perms yourself and try again."
            )
