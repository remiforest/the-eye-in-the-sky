mkdir /teits/
cp settings.py /teits/
cp pilot.py /teits/
cp init.sh /teits/
cp -R TelloPy /teits/
sed -i 's/\/mapr\/demo.mapr.com//g' /teits/init.sh