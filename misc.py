import os


def create_folder(folder_name: str) -> None:
    folder_path = os.path.normcase("./" + folder_name)

    if not os.path.isdir(folder_path):
        try:
            os.mkdir(folder_path, mode=0o750)
        except:
            # This shoudln't ever be reached, as it would imply that the folder doesn't exist, but the script also is unable to create it. Could possibly be missing read permissions if the scripts catches this exception
            raise Exception(f"The folder {folder_name} couldn't be created, exiting")
    else:
        try:
            os.chmod(folder_path, 0o750)
        except:
            raise Exception(
                f"Failed to set the 750 permissions on {folder_name}, either remove the folder or set the right perms yourself and try again."
            )
