import requests

# IPFS hash of the JSON file
ipfs_hash = "QmbhTQ9pcvAmBBHTFE4n78N9wPTykUdJkteVQ8gmvW53To"

# Construct the IPFS gateway URL
url = f"https://ipfs.io/ipfs/{ipfs_hash}"

# Send a GET request
response = requests.get(url)

# Check for successful response
if response.status_code == 200:
  # Parse the JSON data
  data = response.json()
  # Print the data
  print(data)
else:
  print(f"Error retrieving data: {response.status_code}")

