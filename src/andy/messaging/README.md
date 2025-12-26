# Andy's messaging system
### Introduction
This messaging system contains a Server and Client class.
Any Client can send a message to another Client.
The messages get passed through the server; therefore, a client needs to know how to access the server, but does not need to know how to access other clients.
### Examples
Along with the Server and Client classes is the CLI class which demonstrates how to subclass the Client.
CLI stands for Command Line Interface.
Using CLI you can start a conversation with a different CLI client, and you can see a message you type travels to the other client.

For example, open three terminal.
+ In the first terminal start the server:
> python messaging.py
+ In the second terminal start a client:
> python messaging.py Bob Eric
+ In the third terminal start another client:
> python messaging.py Eric Bob

Notes:
1. Names are case sensitive, so "Bob" was capitalized in both clients.
2. The simple CLI program assumes the first name is the client user, and the second name is the friend where messages are to be sent.

Now, in the second terminal type a message for Eric.
> Bob>>How's the weather?

Eric should receive the message.
> Eric>>\
> Bob>>How's the weather?\
> Eric>>

### Implementation Details
+ Messages are held in the server only until a client connects; then all messages are immediatly sent and no longer in the server.
+ By default the localhost is used by Server and Client.
+ Client usernames are case sensitive.
+ For now, a client can only send a message to a single client.
This might change in the future.
+ A new line (\n) character ends each message internally, so do not let clients put them in messages.
This might change in the future.
Should \n be replaced with \r in outgoing messages and vise-versa on incoming messages?
Should the end of message character be customizable?
These are good questions, which I will answer later when I need to.
### History
Originally, I was interested in exploring Asyncio and Sockets.
It turns out that Asyncio has facilities to eliminate the use of "low-level" sockets.
So far asyncio.start_server works very well.

The Server and Client are demonstrated with a user interface mimicking chat.
However, I can forsee a test instrument sending data to another client who stores that data/message into a database.
In other words, this could be used as a data acquisition system instead.
Undoubtedly, there are other uses too.

I intended to keep this code a simple demonstration of asyncio.
The example user interface is minimal.
The method of server handling messages is simple; not complete or complex.
### License
If you can sell this code to someone, more power to you.
BSD License.
My name is Andy Klempau.

