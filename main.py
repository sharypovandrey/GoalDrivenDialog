from components import Field, GoalChain, Goal
from errors import ValidationError
from input_template import InputTemplate


import os


MISTRAL_API_KEY = ""
os.environ['MISTRAL_API_KEY'] = ""


def quantity_validator(value):
    try:
        value = int(value)
    except (ValueError, TypeError):
        raise ValidationError("Quantity must be a valid number")
    if value <= 0:
        raise ValidationError("Quantity cannot be less than one")
    if value > 100:
        raise ValidationError("Quantity cannot be greater than 100")
    return value

class CancelLessonGoal(Goal):
    reason = Field("причина отмены урока (опционально)", format_hint="a string")


class ProductOrderGoal(Goal):
    product_name = Field("товар, который хотят заказать", format_hint="a string")
    customer_email = Field("email покупателя", format_hint="a string")
    quantity = Field(
        "количество товара", format_hint="an integer", validator=quantity_validator
    )


class OrderCancelGoal(Goal):
    reason = Field("причина отмены заказа (опционально)", format_hint="a string")



product_order_goal = ProductOrderGoal(
    label="product_order",
    goal="получить информацию по заказу, который будет сделан",
    opener="Я вижу, что вы хотите сделать заказ. Как я могу вам помочь?",
    out_of_scope="Попросить пользователя связаться с sales@og1.ru",
    model = "mistral/mistral-large-latest",
    json_model = "mistral/mistral-large-latest"
)

product_order_goal = ProductOrderGoal(
    label="product_order",
    goal="получить информацию по заказу, который будет сделан",
    opener="Я вижу, что вы хотите сделать заказ. Как я могу вам помочь?",
    out_of_scope="Попросить пользователя связаться с sales@og1.ru",
    model = "mistral/mistral-large-latest",
    json_model = "mistral/mistral-large-latest"
)

order_cancel_goal = OrderCancelGoal(
    label="cancel_current_order",
    goal="получить причину отмены заказа",
    opener="Я вижу, что вы пытаетесь отменить текущий заказ. Как я могу вам помочь?",
    out_of_scope="Попросить пользователя связаться с support@og1.ru",
    confirm=False,
    model = "mistral/mistral-large-latest",
    json_model = "mistral/mistral-large-latest"
)

product_order_goal.connect(
    goal=order_cancel_goal,
    user_goal="отменить текущий заказ",
    hand_over=True,
    keep_messages=True,
)

order_cancel_goal.connect(
    goal=product_order_goal,
    user_goal="продолжить заказ не смотря ни на что",
    hand_over=True,
    keep_messages=True,
)

goal_chain = GoalChain(product_order_goal)


goal_chain.get_response()
goal_chain.get_response("Я бы хотел заказать пылесос")
goal_chain.get_response("sharypovandrey gmail.com")
goal_chain.get_response("2")
goal_chain.get_response("я не такую модель хотел")
goal_chain.get_response("хотя нет, я куплю просто пылесос")
goal_chain.get_response("подтверждаю")
goal_chain.get_response("Is it a good vacuum cleaner? What do you think?")
goal_chain.get_response("Ok, I’d actually like to make that an order of 500")
goal_chain.get_response("Yes")
goal_chain.get_response("Alright, I’ll guess I’ll just go with 1")
goal_chain.get_response("That’s right")
goal_chain.simulate_response(
    f"Спасибо, что выбрали нас. Ваш заказ скоро будет отправлен",
    rephrase=False,
)
goal_chain.get_response("хочу отменить текущий заказ")
goal_chain.get_response("как проехать на главную улицу?")

