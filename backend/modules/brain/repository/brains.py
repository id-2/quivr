from uuid import UUID

from logger import get_logger
from models.settings import get_supabase_client
from modules.brain.dto.inputs import BrainUpdatableProperties
from modules.brain.entity.brain_entity import BrainEntity, PublicBrain
from modules.brain.repository.interfaces.brains_interface import BrainsInterface
from repository.external_api_secret.utils import build_secret_unique_name

logger = get_logger(__name__)


class Brains(BrainsInterface):
    def __init__(self):
        supabase_client = get_supabase_client()
        self.db = supabase_client

    def create_brain(self, brain):
        response = (
            self.db.table("brains").insert(
                brain.dict(exclude={"brain_definition", "brain_secrets_values"})
            )
        ).execute()

        return BrainEntity(**response.data[0])

    def get_public_brains(self):
        response = (
            self.db.from_("brains")
            .select(
                "id:brain_id, name, description, last_update, brain_type, brain_definition: api_brain_definition(*), number_of_subscribers:brains_users(count)"
            )
            .filter("status", "eq", "public")
            .execute()
        )
        public_brains: list[PublicBrain] = []

        for item in response.data:
            item["number_of_subscribers"] = item["number_of_subscribers"][0]["count"]
            if not item["brain_definition"]:
                del item["brain_definition"]
            else:
                item["brain_definition"] = item["brain_definition"][0]
                item["brain_definition"]["secrets"] = []

            public_brains.append(PublicBrain(**item))
        return public_brains

    def update_brain_last_update_time(self, brain_id):
        self.db.table("brains").update({"last_update": "now()"}).match(
            {"brain_id": brain_id}
        ).execute()

    def get_brain_details(self, brain_id):
        response = (
            self.db.table("brains")
            .select("*")
            .filter("brain_id", "eq", str(brain_id))
            .execute()
        )
        if response.data == []:
            return None
        return BrainEntity(**response.data[0])

    def delete_brain(self, brain_id: str):
        results = (
            self.db.table("brains").delete().match({"brain_id": brain_id}).execute()
        )

        return results

    def update_brain_by_id(
        self, brain_id: UUID, brain: BrainUpdatableProperties
    ) -> BrainEntity | None:
        update_brain_response = (
            self.db.table("brains")
            .update(brain.dict(exclude_unset=True))
            .match({"brain_id": brain_id})
            .execute()
        ).data

        if len(update_brain_response) == 0:
            return None

        return BrainEntity(**update_brain_response[0])

    def get_brain_by_id(self, brain_id: UUID) -> BrainEntity | None:
        # TODO: merge this method with get_brain_details
        response = (
            self.db.from_("brains")
            .select("id:brain_id, name, *")
            .filter("brain_id", "eq", brain_id)
            .execute()
        ).data

        if len(response) == 0:
            return None

        return BrainEntity(**response[0])

    def delete_secret(self, user_id: UUID, brain_id: UUID, secret_name: str) -> bool:
        response = self.db.rpc(
            "delete_secret",
            {
                "secret_name": build_secret_unique_name(
                    user_id=user_id, brain_id=brain_id, secret_name=secret_name
                ),
            },
        ).execute()

        return response.data
