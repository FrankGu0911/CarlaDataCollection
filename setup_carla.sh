#! /usr/bin/env bash

function download_carla_mainland () {
    if [ -e CARLA_0.9.$n.tar.gz ]; then
        echo "File exist!"
    fi
    if ! wget -c https://mirrors.sustech.edu.cn/carla/carla/0.9.$n/CARLA_0.9.$n.tar.gz;
        then echo "There is no version for CARLA 0.9.$n";
    else
        tar -xzf CARLA_0.9.$n.tar.gz
        echo "Finished download CARLA 0.9.$n... ==> now for additional maps"
        cd Import && wget -c https://mirrors.sustech.edu.cn/carla/carla/0.9.$n/AdditionalMaps_0.9.$n.tar.gz
        cd .. && bash ImportAssets.sh
        rm CARLA_0.9.$n.tar.gz Import/AdditionalMaps_0.9.$n.tar.gz
    fi
}

function download_carla () {
    if ! wget -c https://carla-releases.s3.eu-west-3.amazonaws.com/Linux/CARLA_0.9.$n.tar.gz;
        then echo "There is no version for CARLA 0.9.$n";
    else
        tar -xzf CARLA_0.9.$n.tar.gz
        echo "Finished download CARLA 0.9.$n... ==> now for additional maps"
        cd Import && wget -c https://carla-releases.s3.eu-west-3.amazonaws.com/Linux/AdditionalMaps_0.9.$n.tar.gz
        cd .. && bash ImportAssets.sh
        rm CARLA_0.9.$n.tar.gz Import/AdditionalMaps_0.9.$n.tar.gz
    fi
}
# Choose CARLA version
echo "Choose CARLA version to install:"
echo "  - 1) 0.9.13"
echo "  - 2) 0.9.12"
echo "  - 3) 0.9.11"
echo "  - 4) 0.9.10.1"
echo -n "[4] >>> "
read version
version=${version:-4}
if [ "$version" == "1" ]; then
    n=13
elif [ "$version" == "2" ]; then
    n=12
elif [ "$version" == "3" ]; then
    n=11
elif [ "$version" == "4" ]; then
    n=10.1
else
    echo "Invalid version"
    exit 1
fi

# Download CARLA 0.9.13
echo "CARLA 0.9.$n will now be installed into the current directory"
echo "  - Press Ctrl+C to cancel the installation"
echo "  - Press Enter to continue"
echo "  - Or specify a different directory below"
echo -n "[$(pwd)/carla] >>> "
read path
path=${path:-$(pwd)/carla}
mkdir -p "$path"
cd "$path"

# Test ip location
ip_address=$(curl -s http://whatismyip.akamai.com/)
location=$(curl -s "https://api.iplocation.net/?format=json&ip=${ip_address}")

if [[ "$location" == *"country_name\":\"China"* ]]; then
    echo "The current IP address is located in mainland China, so the SUSTech mirror will be used."
    download_carla_mainland
else
    # echo "The current IP address is not located in mainland China, so the official mirror will be used."
    download_carla
fi
