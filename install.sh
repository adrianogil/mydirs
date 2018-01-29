echo '================================'
echo 'Installing mydirs'
echo ''

# Variables
profile_file=~/.profile
mydirs_directory=$(PWD)
mydirs_script=$mydirs_directory/src/mydirs.sh
mydirs_autocomplete_script=$mydirs_directory/src/autocompletion_mydirs.sh

echo ' ' >>  $profile_file
echo '# MyDirs ' >> $profile_file

echo 'Creating alias at '$profile_file
echo 'export MYDIRS_DIRECTORY="'$mydirs_directory'"'
echo 'alias mydirs=". '$mydirs_script'"' >> $profile_file

echo 'Adding autocomplete feature'
echo 'source "'$mydirs_autocomplete_script'"' >> $profile_file
echo ''
echo 'Update '$profile_file
source $profile_file

echo ' '
echo 'Installation completed!'
echo '================================'