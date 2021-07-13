# Used for listing files in directory
import os

# Used for handling relative paths
from pathlib import Path

from OSINTmodules.OSINTscraping import getIamgeForFrontPage


# Function for reading all profile files and returning the content in a list if given no argument, or for returning the contents of one profile if given an argument
def getProfiles(profileName=""):

    profilePath = "./OSINTprofiles/profiles/"

    if profileName == "":
        # Listing all the profiles by getting the OS indepentent path to profiles folder and listing files in it, and then only choosing those files that end in a .profile
        profileFiles = [x for x in os.listdir(path=Path(profilePath)) if ".profile" in x]

        # List for holding the information from all the files, so they only have to be read one
        profiles = list()

        # Reading all the different profile files and storing the contents in just created list
        for profile in profileFiles:

            # Stripping any potential trailing or leading newlines
            profiles.append(Path(profilePath + profile).read_text().strip())

        return profiles
    else:
        return Path(profilePath + profileName + ".profile").read_text().strip()

def collectWebsiteDetails():
    profiles = getProfiles()

    # The final list of all the website information
    details = {}

    for profile in profiles:
        currentProfile = json.loads(profile)

        imageURL = getImageForFrontPage(currentProfile)

        details[currentProfile['source']['profileName']] = {
            'name' : currentProfile['source']['name'],
            'image' : imageURL
        }

    return details
