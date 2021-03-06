''' This module can be thought of as the heart of the entire program. All the messages that are sent
    to the bot are processed here, giving thought to the context in which the message was sent.

    The module processes the message, does the required database operation and returns the correct contextual 
    reply to the calling function.

    FUNCTIONS IN THIS MODULE

    1. return_message() - This function is the heart of the module. The messages sent to the bot are first sent
                          here to be processed. 

    2. process_command() - This function is used to process command messages, commands that start with an
                           exclamation mark are considered to be command messages. The command messages are
                           processed taking the context of the conversation as an argument (transaction_state)
                           For more information on transaction_states, please scroll below to its corresponding
                           section.
    
    3. process_unreg_sender() - This function is called when database_operations.credCheck() returns False for
                                a particular sender_id, which means that the sender isn't registered with the 
                                service.
    
                           
    TRANSACTION STATES
    Transaction states are a property of each message and sender pair. They describe the context in which the sender has 
    sent the message. The transaction state is needed for the bot to give the correct contextual reply to the sender. It
    lets the bot know the context in which a user's message was sent.

    Transaction states are only needed when a line of conversation between the bot and the sender spans more than one
    message and reply. If one message and reply is enough to start and end the conversation between the bot and the sender,
    transaction states won't be used.

    Currently, the transaction states are:

     None - This is the default state for all senders who don't have an ongoing transaction. All conversations between the 
            bot and the sender will start from this state.
    
     0 - This is the state when the sender has initiated a new transaction. At this stage, the sender has to enter the item
         or service that they have purchased.
        
     1 - This is the state after the item has been entered by the sender. At this stage, the sender has to enter the price
         paid for the above stated purchase.

     2 - This is the state after the price of the purchase has been entered by the sender, the sender has to enter the 
         name of the seller of the above purchase.
        
     3 - This is the state after the seller of the purchase has been entered by the sender, ther sender has to enter the
         category that they would like to put this purchase in.
    
     4 - This is the state after the category of the purchase has been entered by the sender. At this stage, all the 
         necessary information regarding a purchase has been entered by the sender, and can now be committed to the 
         main transactions database.

     5 - This is the state after and !abort command has been entered by the sender when they have an ongoing transaction.
         When this stage is entered, a confirmatory check is made to the sender to confirm the abortion of the current
         transaction.

     6 - This is the states after a user has initiated account deletion. At this stage, a confirmatory check is sent to 
         the user to confirm if they really want to delete their account.
                          
'''
import os
import database_operations as db
import api_caller as ac
import replies as r


def return_message(message, sender_id, chat_id):
    transaction_state = db.getTransactionState(sender_id)
    cred_state = db.checkCreds(sender_id)
    print(cred_state)

    if cred_state is False:
        return process_unreg_sender(message, sender_id, transaction_state)

    if message.startswith('!'):
            return process_command(message, transaction_state, sender_id, chat_id)

    if transaction_state is None:
        if message.lower() == 'new':
            db.createNewTransaction(sender_id)
            return r.standard_reply(transaction_state)

        if message.lower() == 'show':
            spending_data = db.lastTenTransactions(sender_id)
            if len(spending_data) == 0:
                return r.special_reply(state = 4)
            ac.sendMsg(chat_id, r.special_reply(state = 3))
            ret_str = ''; i=1
            for row in spending_data:
                article = 'An' if row[0].lower()[0] in ['a', 'e', 'i', 'o', 'u'] else 'A'
                if row[0].lower().endswith('s'):
                    article = '' 
                ret_str+=str(i)+str(r.special_reply(state = 5)).format(
                article, row[0], row[1], row[2], row[3])+'\n\n'
                i+=1
            return ret_str

        if message.lower() == 'delete':
            db.deleteUser(sender_id, state = 1)
            return r.special_reply(state = 6)
            

    elif transaction_state in range(0, 4):

        if transaction_state == 1:
            try:
                float(message)
            except ValueError:
                return r.wrong_input_reply(input_error_code = 1)
            if float(message) <= 0:
                return r.wrong_input_reply(input_error_code = 2)
            message = float(message)

        db.updateTransaction(sender_id, message, transaction_state)
        return r.standard_reply(transaction_state)
    
    elif transaction_state == 5:
        if message == 'y' or message == 'n':
            db.abortTransaction(message, sender_id, transaction_state)
            if message == 'y':
                return r.special_reply(state = 1)    
            ac.sendMsg(chat_id, r.special_reply(state = 2))
            return r.standard_reply(transaction_state=(db.getTransactionState(sender_id)-1))        
        else:
            return r.wrong_input_reply(input_error_code = 3)

    elif transaction_state == 6:
        if message == 'y' or message == 'n':
            if message == 'y':
                db.deleteUser(sender_id, state = 2)
                return r.special_reply(state = 7)
            db.deleteUser(sender_id, state = 3)
            return r.special_reply(state = 8)
        return r.wrong_input_reply(input_error_code = 5)

def process_command(message, transaction_state, sender_id, chat_id):
    if transaction_state is None:
        if message.lower() == '!help':
            return r.command_reply(command = 1)
        
    elif transaction_state in range(0, 4):
        if message.lower() == '!help':
            return r.command_reply(command = 2)
        if message.lower() == '!abort':
            db.abortTransaction(message, sender_id, transaction_state)
            return r.command_reply(command = 3)
        else:
            ac.sendMsg(chat_id, r.command_reply(command = 2))
            return r.standard_reply(transaction_state = transaction_state-1)
    
    elif transaction_state == 5:
        return r.wrong_input_reply(3)

def process_unreg_sender(message, sender_id, transaction_state):
    if transaction_state is None:
        db.createNewTransaction(sender_id)
        return r.unregistered_sender_reply(state = 1)
    if transaction_state == 0:
        if message == 'y' or message == 'n':
            db.deleteNewSender(sender_id)
            if message == 'y':
                db.createAccount(sender_id)
                return r.unregistered_sender_reply(state = 2)
            return r.unregistered_sender_reply(state = 3)
        return r.wrong_input_reply(input_error_code = 4)