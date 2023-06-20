<h1 align="center">Telegram-poll-bot</h1>
<h2>🤖 Bot for polls in Telegram messenger groups.</h2>
This Telegram messenger bot was created to solve the problem of quickly obtaining a user's opinion on the means of using survey results.

<h2>How to install?</h2>
<ol>
  <li>git clone https://github.com/KuganVlad/Telegram-poll-bot.git</li>
  <li>cd Telegram-poll-bot</li>
  <li>pip install -r requirements.txt</li>
  <li>Fill in the token in the config.ini file, substituting the value of your bot token received through @BotFather</li>
  <li>python main.py</li>
  <li>Add a user_id that you can find out via @userinfobot, then put it in the table allowed_users in the database.</li>
</ol>

<h2>How to use?</h2>
After launching the program, add the bot you created to the required groups and chats where you would like to place your polls.
Further control of the bot takes place through an interactively understandable menu, which also provides for the output of statistics.
To grant access to the bot to other users, you must manually enter their identifiers in the user_id column of the allowed_table table of the created database bot.db


<h2>Feedback:</h2>
If you have suggestions, as well as identifying errors, write to me at https://t.me/ulad_ku
