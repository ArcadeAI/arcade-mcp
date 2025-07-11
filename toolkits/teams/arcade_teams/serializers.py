from collections.abc import Callable

from msgraph.generated.models.channel import Channel
from msgraph.generated.models.chat import Chat
from msgraph.generated.models.chat_message import ChatMessage
from msgraph.generated.models.chat_message_attachment import ChatMessageAttachment
from msgraph.generated.models.chat_message_mention import ChatMessageMention
from msgraph.generated.models.chat_message_reaction import ChatMessageReaction
from msgraph.generated.models.conversation_member import ConversationMember
from msgraph.generated.models.identity_set import IdentitySet
from msgraph.generated.models.person import Person
from msgraph.generated.models.physical_address import PhysicalAddress
from msgraph.generated.models.team import Team
from msgraph.generated.models.teamwork_tag import TeamworkTag
from msgraph.generated.models.user import User


def serialize_team(team: Team, transform: Callable | None = None) -> dict:
    team_dict = {
        "id": team.id,
        "name": team.display_name,
        "description": team.description,
        "is_archived": team.is_archived,
    }

    if team.created_date_time:
        team_dict["created_at"] = team.created_date_time.isoformat()

    if team.summary:
        team_dict["members_count"] = team.summary.members_count

    if team.primary_channel:
        team_dict["primary_channel"] = serialize_channel(team.primary_channel)

    if team.members:
        team_dict["members"] = [member.display_name for member in team.members]

    if team.tags:
        team_dict["tags"] = [serialize_tag(tag) for tag in team.tags]

    if transform:
        return transform(team_dict)

    return team_dict


def serialize_channel(channel: Channel, transform: Callable | None = None) -> dict:
    channel_dict = {
        "id": channel.id,
        "name": channel.display_name,
        "description": channel.description,
        "is_archived": channel.is_archived,
    }

    if channel.created_date_time:
        channel_dict["created_at"] = channel.created_date_time.isoformat()

    if channel.summary:
        channel_dict["members_count"] = channel.summary.members_count

    if channel.membership_type:
        channel_dict["membership_type"] = channel.membership_type.value

    if channel.members:
        channel_dict["members"] = [member.display_name for member in channel.members]

    if transform:
        return transform(channel_dict)

    return channel_dict


def serialize_chat(chat: Chat, transform: Callable | None = None) -> dict:
    chat_dict = {
        "id": chat.id,
        "name": chat.display_name,
        "tenant_id": chat.tenant_id,
    }

    if chat.topic:
        chat_dict["topic"] = chat.topic

    if chat.members:
        chat_dict["members"] = [serialize_member(member) for member in chat.members]

    if chat.created_date_time:
        chat_dict["created_at"] = chat.created_date_time.isoformat()

    if transform:
        return transform(chat_dict)

    return chat_dict


def serialize_tag(tag: TeamworkTag) -> dict:
    return {
        "id": tag.id,
        "name": tag.display_name,
    }


def serialize_member(member: ConversationMember, transform: Callable | None = None) -> dict:
    member_dict = {
        "id": member.user_id,
        "name": member.display_name,
        "email": member.email,
    }

    if member.roles:
        member_dict["roles"] = member.roles

    if transform:
        return transform(member_dict)

    return member_dict


def serialize_chat_message(message: ChatMessage, transform: Callable | None = None) -> dict:
    message_dict = {
        "id": message.id,
    }

    content = serialize_message_content(message)
    if content:
        message_dict["content"] = content

    if message.created_date_time:
        message_dict["created_at"] = message.created_date_time.isoformat()

    if message.message_type:
        message_dict["message_type"] = message.message_type.value

    if message.importance:
        message_dict["importance"] = message.importance.value

    if message.web_url:
        message_dict["web_url"] = message.web_url

    if message.mentions:
        message_dict["mentions"] = [serialize_mention(mention) for mention in message.mentions]

    if message.attachments:
        message_dict["attachments"] = [
            serialize_attachment(attachment) for attachment in message.attachments
        ]

    if transform:
        return transform(message_dict)

    return message_dict


def serialize_message_content(message: ChatMessage) -> dict:
    content = {}

    if message.body:
        content["body"] = {
            "body": {
                "text": message.body.content,
                "type": message.body.content_type.value,
            },
        }

    if message.summary:
        content["summary"] = message.summary

    if message.subject:
        content["subject"] = message.subject

    return content


def serialize_attachment(attachment: ChatMessageAttachment) -> dict:
    attachment_dict = {
        "id": attachment.id,
        "name": attachment.name,
        "type": attachment.content_type,
    }

    if attachment.content:
        attachment_dict["data"] = attachment.content

    if attachment.content_url:
        attachment_dict["url"] = attachment.content_url

    return attachment_dict


def serialize_mention(mention: ChatMessageMention, transform: Callable | None = None) -> dict:
    mention_dict = {
        "text": mention.mention_text,
    }

    if mention.mentioned:
        identity = resolve_identity_reference(mention.mentioned)
        if identity:
            mention_dict["identity"] = identity

    if transform:
        return transform(mention_dict)

    return mention_dict


def serialize_chat_reaction(
    reaction: ChatMessageReaction, transform: Callable | None = None
) -> dict:
    reaction_dict = {}

    if reaction.created_date_time:
        reaction_dict["datetime"] = reaction.created_date_time.isoformat()

    if reaction.display_name:
        reaction_dict["name"] = reaction.display_name

    if reaction.reaction_content_url:
        reaction_dict["content_url"] = reaction.reaction_content_url

    if reaction.user:
        reaction_dict["user"] = {
            "id": reaction.user.user.id,
            "name": reaction.user.user.display_name,
        }

    if transform:
        return transform(reaction_dict)

    return reaction_dict


def serialize_person(person: Person, transform: Callable | None = None) -> dict:
    person_dict = {
        "id": person.id,
    }

    enrich_human_name(person_dict, person)
    enrich_person_phones(person_dict, person)
    enrich_person_locations(person_dict, person)
    enrich_person_employment(person_dict, person)

    if person.birthday:
        person_dict["birthday"] = person.birthday

    if person.person_notes:
        person_dict["my_notes_about_this_person"] = person.person_notes

    if person.scored_email_addresses:
        person_dict["emails"] = [email.address for email in person.scored_email_addresses]

    if person.websites:
        person_dict["websites"] = [website.address for website in person.websites]

    if transform:
        return transform(person_dict)

    return person_dict


def enrich_person_phones(person_dict: dict, person: Person) -> list:
    phones = []

    if person.phones:
        for phone in person.phones:
            phone_dict = {}
            if phone.type:
                phone_dict["type"] = phone.type.value

            if phone.number:
                phone_dict["number"] = phone.number

            if phone.region:
                phone_dict["region"] = phone.region

            if phone.language:
                phone_dict["language"] = phone.language

            if phone_dict:
                phones.append(phone_dict)

    if phones:
        person_dict["phones"] = phones

    return person_dict


def enrich_person_employment(person_dict: dict, person: Person) -> dict:
    employment = {}

    if person.company_name:
        employment["company"] = person.company_name

    if person.department:
        employment["department"] = person.department

    if person.job_title:
        employment["job_title"] = person.job_title

    if person.profession:
        employment["profession"] = person.profession

    if person.office_location:
        employment["office_location"] = person.office_location

    if employment:
        person_dict["employment"] = employment

    return person_dict


def enrich_person_locations(person_dict: dict, person: Person) -> dict:
    if not person.postal_addresses:
        return person_dict

    locations = []

    for location in person.postal_addresses:
        location_dict = {}

        enrich_location_address(location_dict, location.address)

        if location.display_name:
            location_dict["name"] = location.display_name

        if location.location_type:
            location_dict["type"] = location.location_type.value

        if location.location_uri:
            location_dict["uri"] = location.location_uri

        if location_dict:
            locations.append(location_dict)

    if locations:
        person_dict["locations"] = locations

    return person_dict


def enrich_location_address(location_dict: dict, address: PhysicalAddress | None) -> dict:
    if not address:
        return location_dict

    address_dict = {}

    if address.street:
        address_dict["street"] = address.street

    if address.city:
        address_dict["city"] = address.city

    if address.state:
        address_dict["state"] = address.state

    if address.country_or_region:
        address_dict["country"] = address.country_or_region

    if address.postal_code:
        address_dict["postal_code"] = address.postal_code

    if address_dict:
        location_dict["address"] = address_dict

    return location_dict


def enrich_human_name(human_dict: dict, human: Person | User) -> dict:
    human_dict["name"] = {
        "display": human.display_name,
    }

    if human.given_name:
        human_dict["name"]["first"] = human.given_name

    if human.surname:
        human_dict["name"]["last"] = human.surname

    return human_dict


def serialize_user(user: User, transform: Callable | None = None) -> dict:
    user_dict = {
        "id": user.id,
    }

    enrich_human_name(user_dict, user)

    if user.created_date_time:
        user_dict["created_at"] = user.created_date_time.isoformat()

    if user.about_me:
        user_dict["about"] = user.about_me

    if user.birthday:
        user_dict["birthday"] = user.birthday.isoformat()

    if user.mobile_phone:
        user_dict["mobile_phone"] = user.mobile_phone

    enrich_user_location(user_dict, user)
    enrich_user_employment(user_dict, user)
    enrich_user_contacts(user_dict, user)

    if transform:
        return transform(user_dict)

    return user_dict


def enrich_user_contacts(user_dict: dict, user: User) -> dict:
    contacts = {}
    email = {}

    if user.mail:
        email["primary"] = user.mail

    if user.other_mails:
        email["secondary"] = user.other_mails

    if user.my_site:
        contacts["site"] = user.my_site

    if user.mobile_phone:
        contacts["mobile_phone"] = user.mobile_phone

    if email:
        contacts["email"] = email

    if contacts:
        user_dict["contacts"] = contacts

    return user_dict


def enrich_user_location(user_dict: dict, user: User) -> dict:
    location = {}

    if user.street_address:
        location["address"] = user.street_address

    if user.city:
        location["city"] = user.city

    if user.state:
        location["state"] = user.state

    if user.country:
        location["country"] = user.country

    if user.postal_code:
        location["postal_code"] = user.postal_code

    if user.office_location:
        location["office"] = user.office_location

    if location:
        user_dict["location"] = location

    return user_dict


def enrich_user_employment(user_dict: dict, user: User) -> dict:
    employment = {}

    if user.company_name:
        employment["company"] = user.company_name

    if user.employee_id:
        employment["employee_id"] = user.employee_id

    if user.employee_type:
        employment["employee_type"] = user.employee_type

    if user.job_title:
        employment["job_title"] = user.job_title

    if user.hire_date:
        employment["hired_at"] = user.hire_date.isoformat()

    if employment:
        user_dict["employment"] = employment

    return user_dict


def resolve_identity_reference(identity_set: IdentitySet) -> dict | None:
    if hasattr(identity_set, "user"):
        return {
            "type": "user",
            "id": identity_set.user.id,
            "name": identity_set.user.display_name,
        }

    if hasattr(identity_set, "conversation"):
        return {
            "type": "conversation",
            "id": identity_set.conversation.id,
            "name": identity_set.conversation.display_name,
        }

    if hasattr(identity_set, "team"):
        return {
            "type": "team",
            "id": identity_set.team.id,
            "name": identity_set.team.display_name,
        }

    return None


def short_version(item: dict, keys: list[str] | None = None) -> dict:
    keys = keys or ["id", "name"]
    return {key: item.get(key) for key in keys}


def short_person(person: dict) -> dict:
    return {
        "id": person["id"],
        "name": person["name"]["display"],
    }
