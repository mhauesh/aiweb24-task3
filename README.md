# Start Code for Task 3

AI & the Web, winter term 2024/2025

## Running the code on your development server

1. Create and activate a virtual environment, install everything from requirements.txt

2. Run hub

    > python hub.py

3. Run the channel server (different shell)

    > python channel.py

4. Register the channel server with the hub (another different shell)

    > flask --app channel.py register
    
5. Now start the client (new shell of shell from 4.) 

    > python client.py

6. Open the client, link is displayed after client start (e.g., http://localhost:5005)


## Creating your own client

1. Set variables in the client code
2. Modify the code

# Deploying on the server

Follow the same steps as for task 2.

Don't forget to adjust the variables in the client code. 

You don't need to run the hub but use the public hub:

http://vm146.rz.uni-osnabrueck.de/hub
SERVER_AUTHKEY = 'Crr-K24d-2N'

You don't need to start your channel explicitly because the Apache server will do that for you.

But don't forget to register your channel server with the hub (see above).