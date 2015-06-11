# test_typing.py ~ python 2.7, mongo 2.4.9 ~ copyright 2015 Paul Beaudet
# collects answers to questions and records answers and speeds to database
# requires a file of new line separated questions

from pymongo import Connection
import Tkinter as Gui
from tkFileDialog import askopenfilename

# layout constants
WINDOW_TITLE = "Test_Typing"
PADDING = 5
COLUMN_WIDTH = 100

# Timing constants
THINKING_TIME = 10    # SECONDS
TYPING_TIME = 20      # SECONDS
CHECK_DURATION = 50  # MILLISECONDS
A_SECOND = 1000       # MILLISECONDS
A_MINUTE = 60000      # MILLISECONDS
A_WORD = 5            # Characters
START_PROMPT = "Select field below, press enter and pick a quiz to start," \
               " %s seconds to think %s, seconds to type" % (THINKING_TIME, TYPING_TIME)
ID = "What is your name?"


class DataCapture:
    def __init__(self):
        # set-up database interface
        con = Connection()
        db = con.first
        self.question = db.questions
        self.name = None  # document is anchored by name of participant

    def new_doc_name(self, name=None):
        if name is None:
            name = self.name  # when no name is the old name is used
            self.question.insert({'name': name})
        else:
            self.name = name  # Whenever a new name is added a new round of questions is assumed

    def add_answer(self, question, answer, speed):
        self.question.update({'name': self.name}, {'$set': {question: {answer: speed}}}, upsert=True)

    def clear_data(self):
        for stuff in self.question.find():
            self.question.remove(stuff)


class WordsPerMinute:
    def __init__(self):
        self.total_time = 0
        self.last_length = 0

    def wpm(self, time, length):
        rate = time / length
        cpm = A_MINUTE / rate
        return cpm / A_WORD

    def running(self, length, total):
        self.total_time += total
        self.last_length = length
        return self.wpm(self.total_time, length)

    def final_wpm(self):
        time = self.total_time
        length = self.last_length
        self.total_time = 0  # reset total time and length when final is called
        self.last_length = 0
        return self.wpm(time, length)


class QueHandler:
    def __init__(self):
        self.questions_to_ask = [ID]  # stores question from a file
        self.que = 0
        self.log = DataCapture()

    def get_questions(self, directory):  # pass the directory of the questions file as an argument
        if directory:  # be sure that a directory was selected
            questions = open(directory)
            for line in questions:  # this assumes all lines in the file in question are questions
                line = line.strip('\n')    # remove new line chars
                self.questions_to_ask.append(line)  # append question to the que array
            questions.close()  # close the file as such to terminate its use
            return True        # signal that questions are locked and loaded
        else:
            return False       # signal directory failed to be obtained

    def next(self, last_answer=False, wpm=0):  # records last answer and returns next question if an answer was given
        question = ""  # Initialize question with start dialog
        if last_answer:
            if self.que < len(self.questions_to_ask)-1:  # This is the case where name is successfully obtained
                if self.que is 0:
                    self.log.new_doc_name(last_answer)  # Log the name
                else:
                    self.log.add_answer(question=self.questions_to_ask[self.que], answer=last_answer, speed=wpm)
                self.que += 1
                question = self.questions_to_ask[self.que]  # set the next question to be returned
            else:  # this is the case where questions are done, !record the last answer
                self.log.add_answer(question=self.questions_to_ask[self.que], answer=last_answer, speed=wpm)
                self.que = 0                  # Reset the index number
                self.questions_to_ask = [ID]  # Reset the question form
                question = START_PROMPT       # return the start prompt to ask the user to go again
        elif self.que is 0:  # Name was not given?
            question = self.questions_to_ask[0]  # Okay well I'm going to keep asking till you id yourself
        return question


class InterfaceGraphic:
    def __init__(self, enter_action, check_entry):
        """ Create main window """
        self.root = Gui.Tk()
        self.root.title(WINDOW_TITLE)
        self.question = Gui.Label(self.root, text=START_PROMPT)
        self.question.grid(row=0, column=1, padx=PADDING, pady=PADDING)
        self.timer = Gui.Label(self.root, text="0", fg="green")
        self.timer.grid(row=0, padx=PADDING, pady=PADDING)
        self.speedometer = Gui.Label(self.root, text="0 WPM")
        self.speedometer.grid(row=0, column=3)
        self.entry_field = Gui.Entry(self.root, width=COLUMN_WIDTH)
        self.entry_field.grid(row=1, columnspan=5, padx=PADDING, pady=PADDING)
        self.entry_field.after(CHECK_DURATION, check_entry)
        self.root.bind('<Return>', enter_action)
        self._job = None

    def answer_size(self):
        return len(self.entry_field.get())

    def update(self, time_color="green", time_left=0, speed="0", question=START_PROMPT):
        self.timer.config(fg=time_color, text=time_left)  # update timer widget
        self.speedometer.config(text=str(speed)+" WPM")
        self.question.config(text=question)

    def take_answer(self):  # grabs answer and deletes it
        answer = self.entry_field.get()
        size = len(answer)
        if size:
            self.entry_field.delete(0, size)
            return answer
        else:
            return False  # return a zero to signify no answer was provided

    def start_timer(self, callback):
        self._job = self.timer.after(A_SECOND, callback)

    def stop_timer(self):
        if self._job is not None:
            self.timer.after_cancel(self._job)
            self._job = None  # after preventing next callback set job to none to signal another callback can be made


class TimeLogic:
    def __init__(self):
        self.timer_stage = 0  # when externally set 1; time sequence starts given the callback is being used
        self.seconds_past = 0  # starts with thinking time on the clock
        self.color = "green"

    def pause(self):
        self.timer_stage = 0
        self.seconds_past = 0
        self.color = "green"

    def think(self):
        self.timer_stage = 1
        self.seconds_past = THINKING_TIME
        self.color = "green"

    def type(self):
        self.timer_stage = 2
        self.seconds_past = TYPING_TIME
        self.color = "red"

    def callback(self):
        if self.timer_stage:  # decrement the clock in stages 1 and 2
            self.seconds_past -= 1
            if self.seconds_past < 1:  # given the clock is finished
                if self.timer_stage is 1:
                    self.type()   # set typing stage
                elif self.timer_stage is 2:
                    return True
        return False


class TypingForm:  # this is where everything comes together
    def __init__(self):
        self.que = QueHandler()        # questions
        self.time = TimeLogic()        # timer widget ~ 2nd version
        self.wpm = WordsPerMinute()    # speedometer
        # Pass graphical user interface callback methods, enter, start-button, entry-field-check
        self.gui = InterfaceGraphic(self.enter_action, self.check_entry)

    def record_verify(self):
        entry = self.gui.take_answer()
        self.gui.stop_timer()  # cancel last timer callback
        next_question = self.que.next(last_answer=entry, wpm=self.wpm.final_wpm())
        if next_question is START_PROMPT:
            self.time.pause()
        else:
            self.time.think()
            self.gui.start_timer(callback=self.timer_callback)
        # regardless make sure question_field dialog is updated and the speedometer is set to 0
        self.gui.update(time_color=self.time.color, time_left=self.time.seconds_past, question=next_question)

    def timer_callback(self):
        if self.time.callback():  # returns true when typing stage ends AKA ran out of time
            self.record_verify()  # this calls for the next second if there are more questions
        else:  # given time still on the clock call for the next second and update timer
            self.gui.start_timer(callback=self.timer_callback)  # pass itself for callback in a second
            self.gui.timer.config(fg=self.time.color, text=self.time.seconds_past)  # update timer widget

    def start_form(self):
        if self.time.timer_stage:
            pass
        elif self.que.get_questions(askopenfilename()):  # given a file was picked with questions in it
            self.gui.entry_field.delete(0, self.gui.answer_size())  # empty entry field
            next_question = self.que.next()                         # get the first question
            self.time.think()                                       # Start thinking
            self.gui.start_timer(callback=self.timer_callback)      # Start the timer
            self.gui.update(time_color=self.time.color, time_left=self.time.seconds_past, question=next_question)
        else:
            print "you have to pick a file that includes lines of questions to start"

    def enter_action(self, bob):
        if self.time.timer_stage is 2:
            self.record_verify()
        elif self.time.timer_stage is 1:
            print "cant enter now"
        else:
            self.start_form()

    def check_entry(self):
        current_text_length = self.gui.answer_size()
        if current_text_length:   # there are three possible scenarios for entry: think, type, paused
            if self.time.timer_stage is 1:  # given that an entry starts to exist toggle to typing mode
                self.gui.stop_timer()  # stop the timer could be in the middle of a second
                self.time.type()
                self.gui.timer.config(fg=self.time.color, text=self.time.seconds_past)  # update timer widget
                self.gui.start_timer(callback=self.timer_callback)  # restart the time for the typing phase
            elif self.time.timer_stage is 2:  # whilst typing report speed in words per minute
                wpm = self.wpm.running(current_text_length, CHECK_DURATION)
                self.gui.speedometer.config(text="%s WPM" % wpm)
            else:  # other cases are blocked to prevent pre-entry
                self.gui.entry_field.delete(0, current_text_length)
        self.gui.entry_field.after(CHECK_DURATION, self.check_entry)  # schedule next callback


if __name__ == "__main__":
    """ RUN MAIN LOOP """
    program = TypingForm()       # init program
    program.gui.root.mainloop()  # run program