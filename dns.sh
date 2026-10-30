#!/bin/sh -e
ZONE=$1
TOKEN=$2
DOMAIN=$3
[ -e /tmp/$DOMAIN ] && OLD=$(cat /tmp/$DOMAIN)

cloudflaredns(){
    ID=$(curl -s "https://api.cloudflare.com/client/v4/zones/$ZONE/dns_records?name=$DOMAIN" -H "Authorization: Bearer $TOKEN" | head -1 | cut -d'"' -f6)
	if [ -z "$ID" ]; then
		echo "ID not found"
	else
		STATUS=$(curl -s -X PUT "https://api.cloudflare.com/client/v4/zones/$ZONE/dns_records/$ID" -H "Authorization: Bearer $TOKEN" -H "Content-Type:application/json" -d '{"type":"'"AAAA"'","name":"'"$DOMAIN"'","content":"'"$NEW"'","ttl":1,"proxied":false}' | sed 's/.*"success":\([a-z]\+\).*/\1/')
		if [ "$STATUS" = "true" ]; then
			echo $NEW > /tmp/$DOMAIN
		fi
		echo "$(date) $NEW $STATUS"
	fi
}

NEW=$(ip -6 addr list scope global | sed -n 's/.*inet6 \([0-9a-f:]\+\).*/\1/p' | head -n 1)

if [ -z "$NEW" ]; then
	echo "No new IP found"
elif [ "$OLD" = "$NEW" ]; then
	echo "$(date) $NEW IP address unchanged"
else
	cloudflaredns
fi
