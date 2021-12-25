from OSINTmodules.OSINTprofiles import getProfiles


def verifyProfiles(profiles, esClient):
    # Getting the profiles that are stored in the database
    DBStoredProfiles = esClient.requestProfileListFromDB()

    # Getting the names of the locally avaiable profiles stored in the json files
    localProfiles = getProfiles(justNames = True)

    # Looping through the profiles we want to confirm are matching those stored
    for profile in profiles:
        if profile not in DBStoredProfiles or profile not in localProfiles:
            return False

    return True
