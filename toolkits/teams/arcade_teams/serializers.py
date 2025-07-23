import datetime
import json
from collections.abc import Callable
from typing import Any, cast

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
from msgraph.generated.models.search_hit import SearchHit
from msgraph.generated.models.team import Team
from msgraph.generated.models.teamwork_tag import TeamworkTag
from msgraph.generated.models.user import User


def serialize_team(
    team: Team, transform: Callable[[dict[str, Any]], dict[str, Any]] | None = None
) -> dict[str, Any]:
    team_dict: dict[str, Any] = {
        "object_type": "team",
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


def serialize_channel(
    channel: Channel, transform: Callable[[dict[str, Any]], dict[str, Any]] | None = None
) -> dict[str, Any]:
    channel_dict: dict[str, Any] = {
        "object_type": "channel",
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
        membership_type = cast(str, channel.membership_type.value)
        if membership_type == "standard":
            membership_type = "publicly_visible_to_team_members"
        channel_dict["membership_type"] = membership_type

    if channel.members:
        channel_dict["members"] = [member.display_name for member in channel.members]

    if transform:
        return transform(channel_dict)

    return channel_dict


def serialize_chat(
    chat: Chat, transform: Callable[[dict[str, Any]], dict[str, Any]] | None = None
) -> dict[str, Any]:
    chat_dict: dict[str, Any] = {
        "object_type": "chat",
        "id": chat.id,
        "tenant_id": chat.tenant_id,
    }

    if chat.chat_type:
        chat_dict["type"] = chat.chat_type.value

    if chat.pinned_messages:
        chat_dict["pinned_messages"] = [
            serialize_chat_message(message.message)
            for message in chat.pinned_messages
            if isinstance(message.message, ChatMessage)
        ]

    if chat.web_url:
        chat_dict["web_url"] = chat.web_url

    if chat.topic:
        chat_dict["topic"] = chat.topic

    if chat.members:
        chat_dict["members"] = [serialize_member(member) for member in chat.members]

    if chat.created_date_time:
        chat_dict["created_at"] = chat.created_date_time.isoformat()

    if transform:
        return transform(chat_dict)

    return chat_dict


def serialize_tag(tag: TeamworkTag) -> dict[str, Any]:
    return {
        "object_type": "tag",
        "id": tag.id,
        "name": tag.display_name,
    }


def serialize_member(
    member: ConversationMember, transform: Callable[[dict[str, Any]], dict[str, Any]] | None = None
) -> dict[str, Any]:
    member_dict: dict[str, Any] = {
        "object_type": "conversation_member",
        "name": member.display_name,
    }

    if hasattr(member, "user_id"):
        member_dict["id"] = member.user_id

    elif hasattr(member, "email") and member.email:
        member_dict["email"] = member.email

    if member.roles:
        member_dict["roles"] = member.roles

    if transform:
        return transform(member_dict)

    return member_dict


def serialize_chat_message(
    message: ChatMessage, transform: Callable[[dict[str, Any]], dict[str, Any]] | None = None
) -> dict[str, Any]:
    message_dict: dict[str, Any] = serialize_message_metadata(message)

    content = serialize_message_content(message)
    if content:
        message_dict["content"] = content

    if message.mentions:
        message_dict["mentions"] = serialize_mentions(message.mentions)

    if message.attachments:
        attachments = [
            serialize_attachment(attachment)
            for attachment in message.attachments
            if attachment.content_type != "messageReference"
        ]
        if attachments:
            message_dict["attachments"] = attachments

    # This will only be available in channel messages
    if message.replies:
        message_dict["replies"] = [
            serialize_chat_message(reply, transform) for reply in message.replies
        ]

    # In chat messages, replies are available as attachments
    if message.attachments:
        replies = serialize_message_replies_from_attachments(message)
        if replies:
            message_dict["replying_to"] = replies

    if transform:
        return transform(message_dict)

    return message_dict


def serialize_chat_message_search_hit(search_hit: SearchHit) -> dict[str, Any]:
    message_dict: dict[str, Any] = {
        "object_type": "search_message_hit",
        "summary": search_hit.summary,
    }

    if search_hit.resource:
        if hasattr(search_hit.resource, "id") and search_hit.resource.id:
            message_dict["message_id"] = search_hit.resource.id

        if hasattr(search_hit.resource, "additional_data") and search_hit.resource.additional_data:
            metadata = search_hit.resource.additional_data
            if metadata:
                message_dict.update(serialize_search_hit_metadata(metadata))

    return message_dict


def serialize_search_hit_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
    message_dict: dict[str, Any] = {}

    if metadata.get("webLink"):
        message_dict["web_url"] = metadata["webLink"]

    if isinstance(metadata.get("createdDateTime"), datetime.datetime):
        message_dict["created_at"] = metadata["createdDateTime"].isoformat()

    if metadata.get("importance"):
        message_dict["importance"] = metadata["importance"]

    if metadata.get("subject"):
        message_dict["subject"] = metadata["subject"]

    if isinstance(metadata.get("author"), dict):
        message_dict["author"] = {
            "user_name": metadata["author"].get("name"),
            "microsoft_email_address": metadata["author"].get("emailAddress"),
        }

    if metadata.get("channelIdentity"):
        message_dict["channel_id"] = metadata["channelIdentity"].get("channelId")

    elif metadata.get("chatId"):
        message_dict["chat_id"] = metadata["chatId"]

    return message_dict


def serialize_message_metadata(message: ChatMessage) -> dict:
    message_dict: dict[str, Any] = {
        "object_type": "message",
        "id": message.id,
    }

    if message.from_ and message.from_.user:
        message_dict["author"] = {
            "user_id": message.from_.user.id,
            "user_name": message.from_.user.display_name,
        }

    if message.created_date_time:
        message_dict["created_at"] = message.created_date_time.isoformat()

    if message.message_type:
        message_dict["message_type"] = message.message_type.value

    if message.importance:
        message_dict["importance"] = message.importance.value

    if message.web_url:
        message_dict["web_url"] = message.web_url

    return message_dict


def serialize_message_replies_from_attachments(message: ChatMessage) -> list[dict[str, Any]]:
    replies: list[dict[str, Any]] = []
    if not message.attachments:
        return replies
    for attachment in message.attachments:
        if attachment.content_type == "messageReference" and isinstance(attachment.content, str):
            data = json.loads(attachment.content)
            replies.append({
                "id": data["messageId"],
                "preview": data["messagePreview"],
                "author": {
                    "user_id": data["messageSender"].get("user", {}).get("id"),
                    "name": data["messageSender"].get("user", {}).get("displayName"),
                },
            })
    return replies


def serialize_message_content(message: ChatMessage) -> dict:
    content: dict[str, Any] = {}

    if message.body:
        message_type = message.body.content_type.value if message.body.content_type else "text"
        content["text"] = serialize_message_body_text(message)
        content["type"] = message_type

    if message.summary:
        content["summary"] = message.summary

    if message.subject:
        content["subject"] = message.subject

    return content


def serialize_message_body_text(message: ChatMessage) -> str:
    if not message.body or not message.body.content:
        return ""

    try:
        if message.mentions:
            text = serialize_message_body_text_with_mentions(message)

        if message.attachments:
            for attachment in message.attachments:
                if attachment.content_type == "messageReference":
                    try:
                        data = json.loads(attachment.content)  # type: ignore[arg-type]
                    except (json.JSONDecodeError, ValueError, TypeError):
                        continue

                    pattern = f'<attachment id="{data["messageId"]}"></attachment>'
                    reply = (
                        f'<blockquote type="reply" message_id="{data["messageId"]}" '
                        f'author="{data["messageSender"].get("user", {}).get("displayName", "")}">'
                        f"{data['messagePreview']}</blockquote>"
                    )
                    text = text.replace(pattern, reply)
                else:
                    pattern = f'<attachment id="{attachment.id}"></attachment>'
                    text = text.replace(
                        pattern, f'<attachment id="{attachment.id}">{attachment.name}</attachment>'
                    )
    except Exception:
        text = str(message.body.content)
    return text


def serialize_message_body_text_with_mentions(message: ChatMessage) -> str:
    if not message.body or not message.body.content:
        return ""

    text = str(message.body.content).replace("&nbsp;", " ")

    if not message.mentions:
        return text

    user_ids_seen: set[str] = set()
    mentions_dicts = serialize_mentions(message.mentions)
    mentions_by_id = {mention["id"]: mention for mention in mentions_dicts}

    for mention in message.mentions:
        if not mention.mentioned or not mention.mentioned.user:
            pattern = f'<at id="{mention.id}">{mention.mention_text}</at>'
            text = text.replace(pattern, f"<mention>@{mention.mention_text}</mention>")
            continue

        if mention.mentioned.user.id in user_ids_seen:
            pattern = f'<at id="{mention.id}">{mention.mention_text}</at>'
            text = text.replace(pattern, "")
            continue
        user_ids_seen.add(mention.mentioned.user.id)
        user_name = mentions_by_id[mention.mentioned.user.id]["name"]
        text = text.replace(
            f'<at id="{mention.id}">{mention.mention_text}</at>',
            f'<mention user_id="{mention.mentioned.user.id}">@{user_name}</mention>',
        )

    return text


def serialize_attachment(attachment: ChatMessageAttachment) -> dict[str, Any]:
    attachment_dict: dict[str, Any] = {
        "object_type": "attachment",
        "id": attachment.id,
        "name": attachment.name,
        "type": attachment.content_type,
    }

    if attachment.content:
        attachment_dict["data"] = attachment.content

    if attachment.content_url:
        attachment_dict["url"] = attachment.content_url

    return attachment_dict


def serialize_mentions(mentions: list[ChatMessageMention]) -> list[dict[str, Any]]:
    mentions_by_id: dict[str, Any] = {}
    mentions_list: list[dict[str, Any]] = []
    serialized_mentions = [serialize_mention(mention) for mention in mentions]
    for mention in serialized_mentions:
        if not mention.get("id"):
            mentions_list.append(mention)
            continue

        if mention["id"] not in mentions_by_id:
            mentions_by_id[mention["id"]] = mention
        else:
            mentions_by_id[mention["id"]]["name"] += f" {mention['name']}"
    mentions_list.extend(list(mentions_by_id.values()))
    return mentions_list


def serialize_mention(
    mention: ChatMessageMention, transform: Callable[[dict[str, Any]], dict[str, Any]] | None = None
) -> dict[str, Any]:
    if not mention.mentioned:
        mention_dict: dict[str, Any] = {
            "name": mention.mention_text,
        }
    else:
        mention_dict = resolve_identity_reference(mention.mentioned)  # type: ignore[assignment]

    if transform:
        return transform(mention_dict)

    return mention_dict


def serialize_chat_reaction(
    reaction: ChatMessageReaction,
    transform: Callable[[dict[str, Any]], dict[str, Any]] | None = None,
) -> dict[str, Any]:
    reaction_dict: dict[str, Any] = {}

    if reaction.created_date_time:
        reaction_dict["datetime"] = reaction.created_date_time.isoformat()

    if reaction.display_name:
        reaction_dict["name"] = reaction.display_name

    if reaction.reaction_content_url:
        reaction_dict["content_url"] = reaction.reaction_content_url

    if reaction.user:
        reaction_dict["user"] = {
            "id": reaction.user.user.id,  # type: ignore[union-attr]
            "name": reaction.user.user.display_name,  # type: ignore[union-attr]
        }

    if transform:
        return transform(reaction_dict)

    return reaction_dict


def serialize_person(
    person: Person, transform: Callable[[dict[str, Any]], dict[str, Any]] | None = None
) -> dict[str, Any]:
    person_dict: dict[str, Any] = {
        "object_type": "person",
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


def enrich_person_phones(person_dict: dict[str, Any], person: Person) -> dict[str, Any]:
    phones: list[dict[str, Any]] = []

    if person.phones:
        for phone in person.phones:
            phone_dict: dict[str, Any] = {}
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


def enrich_person_employment(person_dict: dict[str, Any], person: Person) -> dict[str, Any]:
    employment: dict[str, Any] = {}

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


def enrich_person_locations(person_dict: dict[str, Any], person: Person) -> dict[str, Any]:
    if not person.postal_addresses:
        return person_dict

    locations: list[dict[str, Any]] = []

    for location in person.postal_addresses:
        location_dict: dict[str, Any] = {}

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


def enrich_location_address(
    location_dict: dict[str, Any], address: PhysicalAddress | None
) -> dict[str, Any]:
    if not address:
        return location_dict

    address_dict: dict[str, Any] = {}

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


def enrich_human_name(human_dict: dict[str, Any], human: Person | User) -> dict[str, Any]:
    human_dict["name"] = {}

    if human.display_name:
        human_dict["name"]["display"] = human.display_name

    if human.given_name:
        human_dict["name"]["first"] = human.given_name

    if human.surname:
        human_dict["name"]["last"] = human.surname

    return human_dict


def serialize_user(
    user: User, transform: Callable[[dict[str, Any]], dict[str, Any]] | None = None
) -> dict[str, Any]:
    user_dict: dict[str, Any] = {
        "object_type": "user",
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


def enrich_user_contacts(user_dict: dict[str, Any], user: User) -> dict[str, Any]:
    contacts: dict[str, Any] = {}
    email: dict[str, Any] = {}

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


def enrich_user_location(user_dict: dict[str, Any], user: User) -> dict[str, Any]:
    location: dict[str, Any] = {}

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


def enrich_user_employment(user_dict: dict[str, Any], user: User) -> dict[str, Any]:
    employment: dict[str, Any] = {}

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


def resolve_identity_reference(identity_set: IdentitySet) -> dict[str, Any] | None:
    if getattr(identity_set, "user", None) and isinstance(identity_set.user, User):
        return {
            "type": "user",
            "id": identity_set.user.id,
            "name": identity_set.user.display_name,
        }

    if getattr(identity_set, "conversation", None):
        return {
            "type": "conversation",
            "id": getattr(identity_set.conversation, "id", None),  # type: ignore[attr-defined]
            "name": getattr(identity_set.conversation, "display_name", None),  # type: ignore[attr-defined]
        }

    if getattr(identity_set, "team", None):
        return {
            "type": "team",
            "id": getattr(identity_set.team, "id", None),  # type: ignore[attr-defined]
            "name": getattr(identity_set.team, "display_name", None),  # type: ignore[attr-defined]
        }

    return None


def short_version(item: dict[str, Any], keys: list[str] | None = None) -> dict[str, Any]:
    keys = keys or ["id", "name"]
    return {key: item.get(key) for key in keys}


def short_human(human: dict[str, Any], with_email: bool = False) -> dict[str, Any]:
    person_dict: dict[str, Any] = {"id": human["id"], "name": {}}

    display = human["name"].get("display")
    first = human["name"].get("first")
    last = human["name"].get("last")

    if display:
        person_dict["name"]["display"] = display
    elif first and last:
        person_dict["name"]["first"] = first
        person_dict["name"]["last"] = last
    elif first:
        person_dict["name"]["first"] = first
    elif last:
        person_dict["name"]["last"] = last
    else:
        del person_dict["name"]

    if with_email:
        if human.get("email"):
            person_dict["email"] = human["email"]
        elif human.get("emails"):
            person_dict["emails"] = human["emails"]

    return person_dict
