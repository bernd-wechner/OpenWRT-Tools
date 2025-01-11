#!/bin/bash

# Check if openssl is installed
if ! command -v openssl &> /dev/null; then
  echo "openssl is not installed. Please install it."
  exit 1
fi

# Check if a certificate file is provided
if [ -z "$1" ]; then
    CERT_FILE="/etc/lighttpd/ssl/thumbs.place/thumbs.place.cer"
else
    CERT_FILE="$1"
fi


# Check if the certificate file exists
if [ ! -f "$CERT_FILE" ]; then
  echo "Error: Certificate file '$CERT_FILE' not found."
  exit 1
fi

# Extract the subject alternative names (SANs) which contain the domains
SANs=$(openssl x509 -in "$CERT_FILE" -noout -text | awk '/X509v3 Subject Alternative Name:/ {getline; gsub(/^\s+|\s+$/, "", $0); print}')

cleaned_SANs=$(echo "$SANs" | sed 's/DNS://g')

# Extract the expiry date
expiry_date=$(openssl x509 -in "$CERT_FILE" -noout -enddate)
formatted_date=$(echo "$expiry_date" | cut -d= -f2 | sed 's/ GMT$//')

# Print results
echo "Expires: $formatted_date"

echo "Domains:"
IFS=',' read -r -a domains <<< "$cleaned_SANs" # Read into array using comma as delimiter

for domain in "${domains[@]}"; do
    printf "\t%s\n" "$(echo $domain | xargs)"
done

exit 0
