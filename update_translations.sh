 #!/bin/bash
 #You need lingua and gettext installed to run this
 
 echo "Updating voteit.schulze.pot"
 pot-create -d voteit.schulze -o voteit/schulze/locale/voteit.schulze.pot .
 echo "Merging Swedish localisation"
 msgmerge --update voteit/schulze/locale/sv/LC_MESSAGES/voteit.schulze.po voteit/schulze/locale/voteit.schulze.pot
 echo "Updated locale files"
 