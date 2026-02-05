import json
import configparser

CurrentContent = """[usman]
type = sftp
host = staging.cyberpanel.net
user = example_user
pass = PLACEHOLDER_PASSWORD

shell_type = unix
md5sum_command = md5sum
sha1sum_command = sha1sum

[habbitest2gdrive]
type = drive
client_id = ""
client_secret = ""
scope = drive
root_folder_id = ""
service_account_file = ""
token = {"access_token":"PLACEHOLDER_ACCESS_TOKEN","token_type":"Bearer","refresh_token":"PLACEHOLDER_REFRESH_TOKEN"}
"""

# Read the configuration string
config = configparser.ConfigParser()
config.read_string(CurrentContent)

# Get the refresh token
refresh_token = json.loads(config.get('habbitest2gdrive', 'token'))['refresh_token']
old_access_token = json.loads(config.get('habbitest2gdrive', 'token'))['access_token']
print(refresh_token)

new_token ="jdskjkvnckjdfvnjknvkvdjc"
new_string = CurrentContent.replace(str(old_access_token), new_token)

print(new_string)