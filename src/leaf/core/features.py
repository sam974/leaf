'''
Leaf Package Manager

@author:    Sébastien MB <smassot@sierrawireless.com>
@copyright: 2018 Sierra Wireless. All rights reserved.
@contact:   Legato Tooling Team <developerstudio@sierrawireless.com>
@license:   https://www.mozilla.org/en-US/MPL/2.0/
'''


class FeatureManager():
    '''
    Class used to manage features
    '''

    def __init__(self, packageManager):
        self.features = {}

        def visit(mfList):
            for mf in mfList:
                for name, feature in mf.getFeaturesMap().items():
                    if name not in self.features:
                        self.features[name] = feature
                    else:
                        self.features[name].addAlias(feature)
        visit(packageManager.listAvailablePackages().values())
        visit(packageManager.listInstalledPackages().values())

    def getFeature(self, name):
        if name not in self.features:
            raise ValueError("Cannot find feature %s" % name)
        return self.features[name]

    def toggleUserFeature(self, name, enum, pm):
        feature = self.getFeature(name)
        key = feature.getKey()
        value = feature.getValue(enum)
        if value is not None:
            pm.updateUserEnv(setMap={key: value})
        else:
            pm.updateUserEnv(unsetList=[key])

    def toggleWorkspaceFeature(self, name, enum, ws):
        feature = self.getFeature(name)
        key = feature.getKey()
        value = feature.getValue(enum)
        if value is not None:
            ws.updateWorkspaceEnv(setMap={key: value})
        else:
            ws.updateWorkspaceEnv(unsetList=[key])

    def toggleProfileFeature(self, name, enum, ws):
        feature = self.getFeature(name)
        currentProfileName = ws.getCurrentProfileName()
        profile = ws.getProfile(currentProfileName)
        key = feature.getKey()
        value = feature.getValue(enum)
        if value is not None:
            profile.updateEnv(setMap={key: value})
        else:
            profile.updateEnv(unsetList=[key])
        ws.updateProfile(profile)