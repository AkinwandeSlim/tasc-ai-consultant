# Task: Classify Intent

Classify the visitor's message into exactly one intent category.

Available intents:
- describe_problem: Visitor explains a business pain
- answer_question: Response to Nova's discovery question
- company_question: Asks about Trizen experience or capability
- capability_question: Asks whether Trizen can do a specific thing
- pricing_question: Asks about cost
- timeline_question: Asks about duration
- objection: Doubt, comparison, hesitation
- request_human: Asks to speak to a person
- smalltalk: Greeting, thanks, filler
- off_topic: Unrelated to business or Trizen
- anti_persona: Job seeker, vendor, student, competitor
- end_conversation: Signals they are finished

Visitor message: {{ message }}
