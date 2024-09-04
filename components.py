import json
import inspect
from litellm import completion
from input_template import InputTemplate

class Field:
    def __init__(self, description, format_hint=None, validator=None):
        self.description = description
        self.format_hint = format_hint
        self.validator = validator


class Goal:
    def _format_flag(self, flag):
        return f"<{flag}>"
    
    def __init__(self,
                 label,
                 goal,
                 opener, 
                 out_of_scope=None, 
                 confirm=True, 
                 model="gpt-4-1106-preview", 
                 json_model="gpt-4-1106-preview",
                 params = {}):
        self.label = label
        self.goal = goal
        self.opener = opener
        self.confirm = confirm
        self.out_of_scope = out_of_scope
        self.model = model
        self.json_model = json_model
        self.messages = []
        self.connected_goals = []
        self.completed_string = "completed"
        self.hand_over = False    
        self.completed = False
        self.params = params
        
        self.goal_prompt = InputTemplate("""Ваша роль заключается в продолжении беседы ниже в качестве Ассистента.
Цель: {{goal}}
{% if information_list %}
Необходимая информация для сбора: {{information_list|join(", ")}}
Это вся информация, которую вам нужно собрать, не спрашивайте ничего другого.
{% if confirmation %}
Когда получите информацию, запросите подтверждение.
Если вы получите это подтверждение, ответьте только:
{{ completed_string | format_flag }}
{% else %}
Как только получите информацию, ответьте только:
{{ completed_string | format_flag }}
{% endif %}
{% endif %}
{% if out_of_scope %}
{% for goal in connected_goals %}
Если пользователь хочет {{ goal.user_goal }}, ответьте только:
{{ goal.goal.label | format_flag }}
{% endfor %}
Для всего, что выходит за рамки цели:
{{ out_of_scope }}
{% endif %}
Отвечайте естественно и не повторяйтесь.
Беседа до сих пор:
{% for message in messages %}
{{ message.actor }}: {{ message.content }}
{% endfor %}
Ассистент:""", filters={"format_flag": self._format_flag})
        self.completed_prompt = InputTemplate("""На основании беседы ниже выведите JSON, который включает только следующие ключи:
{% for field in fields %}
{{ field.name }}: {{ field.description }} {% if field.format_hint %}({{field.format_hint}})
{% endif %}
{% endfor %}
Если какие-либо ключи не указаны в беседе, установите их значения в null.
Беседа:
{% for message in messages %}
{{ message.actor }}: {{ message.content }}
{% endfor %}""")
        self.error_prompt = InputTemplate("""Извините, но я испытываю трудности с обработкой этого запроса прямо сейчас.""")
        self.validation_prompt = InputTemplate("""Ваша роль заключается в продолжении беседы ниже в качестве Ассистента.
К сожалению, у вас возникли проблемы с обработкой запроса пользователя по следующим причинам:
{% for error in validation_error_messages %}
* {{ error }}
{% endfor %}
Продолжайте беседу естественно и объясните проблемы.
Не проявляйте креативность. Не предлагайте способы исправления проблем.
Беседа до сих пор:
{% for message in messages %}
{{ message.actor }}: {{ message.content }}
{% endfor %}
Ассистент:""")
        self.rephrase_prompt = InputTemplate("""
Ваша роль заключается в продолжении беседы ниже в качестве Ассистента.
Обычно вы отвечаете: {{ response }}
{% if message_history %}
Цель: {{goal}}
Но теперь вам нужно учитывать предыдущую беседу и соответствующим образом адаптировать ваш ответ.
Продолжайте беседу естественно. Не проявляйте креативность.
Беседа до сих пор:
{% for message in message_history %}
{{ message.actor }}: {{ message.content }}
{% endfor %}
{% else %}
Просто перефразируйте ваш ответ в качестве Ассистента.
{% endif %}
Ассистент:""")
        
    def get_fields(self):
        fields = inspect.getmembers(self)
        field_dict = {}
        for field in fields:
            if type(field[1]) == Field:
                field_dict[field[0]] = field[1]
        return field_dict

    def _get_goal_details(self):
        prompt_details = {
            "goal": self.goal,
            "confirmation": self.confirm,
            "messages": self.messages,
            "completed_string": self.completed_string,
            "out_of_scope": self.out_of_scope,
            "connected_goals": self.connected_goals,
        }
        
        fields = self.get_fields()
        information_list = []
        for label, field in fields.items():
            information_list.append(field.description)
        prompt_details["information_list"] = information_list
        return prompt_details
    
    def _get_completion_details(self):
        prompt_details = {
            "messages": self.messages,
        }
        
        fields = self.get_fields()
        field_list = []
        for label, field in fields.items():
            field_list.append(
                {
                    "name": label,
                    "description": field.description,
                    "format_hint": field.format_hint,
                }
            )
        prompt_details["fields"] = field_list
        return prompt_details
    
    def _inference(self, user_message, system_prompt = "", json_mode = False):
        llm_messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ]
        if json_mode:
            response_format = {"type": "json_object"}
            model = self.json_model
        else:
            response_format = None
            model = self.model
        llm_response = completion(
            messages=llm_messages,
            model=model, 
            response_format=response_format,
            **self.params
        )
        llm_response_text = llm_response["choices"][0]["message"]["content"]
        return llm_response_text
    
    def simulate_response(self, response, rephrase = False, message_history = []):
        if rephrase:
            rephrase_details = {
                "response": response,
                "message_history": message_history,
                "goal": self.goal,
            }
            rephrase_pre_prompt = self.rephrase_prompt.text(rephrase_details)
            response = self._inference(
                rephrase_pre_prompt
            )
        self.messages.append(
            {
                "actor": "Assistant",
                "content": response,
            }
        )
        return response
    
    def user_response(self, response):
        self.messages.append(
            {
                "actor": "User",
                "content": response,
            }
        )
        return response
    
    def get_response(self, user_input):
        if not self.messages and not user_input and not self.hand_over:
            return self.simulate_response(self.opener)
        elif not self.messages and not user_input and self.hand_over:
            return self.simulate_response(self.opener, rephrase=True)
        else:
            if user_input:
                user_input = self.user_response(user_input)
            response_text = self._inference(
                self.goal_prompt.text(self._get_goal_details())
            )
            
            # if HANDING OVER
            for connected_goal in self.connected_goals:
                if self._format_flag(connected_goal["goal"].label).lower() in response_text.lower():
                    if connected_goal["keep_messages"]:
                        hand_over_messages = self.messages
                    else:
                        hand_over_messages = []
                    return connected_goal["goal"].take_over(messages = hand_over_messages, hand_over = connected_goal["hand_over"])
            
            # if COMPLETED
            if self._format_flag(self.completed_string).lower() in response_text.lower():

                json_response_text = self._inference(
                    self.completed_prompt.text(self._get_completion_details()),
                    json_mode=True)
                
                try:
                    response_object = json.loads(json_response_text)
                    
                    validation_error_messages = []
                    fields = self.get_fields()
                    
                    for label, field in fields.items():
                        if label in response_object:
                            if field.validator:
                                try:
                                    response_object[label] = field.validator(response_object[label])
                                except ValidationError as e:
                                    validation_error_messages.append(e)
                                        
                    if not validation_error_messages:
                        completed = True
                        return response_object
                    else:
                        validation_details = {
                            "validation_error_messages": validation_error_messages,
                            "messages": self.messages
                        }
                        validation_pre_prompt = self.validation_prompt.text(validation_details)
                        
                        validation_response_text = self._inference(
                            validation_pre_prompt
                        )
                        
                        return self.simulate_response(validation_response_text)
                    
                except json.JSONDecodeError:
                    error_response = error_prompt.text()
                    return self.simulate_response(error_response)

            else:
                return self.simulate_response(response_text)
    
    def take_over(self, messages = [], hand_over = False):
        self.completed = False
        if messages:
            self.messages = messages
        else:
            self.messages = []
        if hand_over:
            self.hand_over = True
        return self
    
    def connect(self, goal, user_goal, hand_over = False, keep_messages = False):
        self.connected_goals.append(
            {
                "goal": goal,
                "user_goal": user_goal,
                "hand_over": hand_over,
                "keep_messages": keep_messages,
            }
        )
        return goal

class GoalChain:
    def __init__(self, starting_goal):
        self.goal = starting_goal
    
    def get_response(self, user_input = None):
        response = self.goal.get_response(user_input)
        if isinstance(response, str):
            return {"type": "message", "content": response, "goal": self.goal}
        elif isinstance(response, dict):
            return {"type": "data", "content": response, "goal": self.goal}
        elif isinstance(response, Goal):
            self.goal = response
            return self.get_response(None)
        else:
            raise TypeError("Unexpected Goal response type")
            
    def simulate_response(self, user_input, rephrase = False):
        response = self.goal.simulate_response(user_input, rephrase = rephrase)
        return {"type": "message", "content": response, "goal": self.goal}