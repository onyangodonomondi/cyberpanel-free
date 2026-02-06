#!/usr/bin/env bash
/usr/local/lsws/lsphp81/bin/php -r "copy('https://getcomposer.org/installer', 'composer-setup.php');"
/usr/local/lsws/lsphp81/bin/php composer-setup.php
/usr/local/lsws/lsphp81/bin/php -r "unlink('composer-setup.php');"
mv composer.phar /usr/bin/composer