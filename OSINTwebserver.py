from OSINTmodules import OSINTdatabase, OSINTprofiles


def collectFeedDetails(OGTags):
    listCollection = {}
    for detailList in ['id', 'url', 'image', 'title', 'description']:
        listCollection[detailList] = [article[detailList] for article in OGTags]
    return listCollection


def verifyProfiles(profiles, connection, tableName):
    # Getting the profiles that are stored in the database
    DBStoredProfiles = OSINTdatabase.requestProfileListFromDB(connection, tableName)

    # Getting the names of the locally avaiable profiles stored in the json files
    localProfiles = OSINTprofiles.getProfiles(justNames = True)

    # Looping through the profiles we want to confirm are matching those stored
    for profile in profiles:
        if profile not in DBStoredProfiles or profile not in localProfiles:
            return False

    return True
