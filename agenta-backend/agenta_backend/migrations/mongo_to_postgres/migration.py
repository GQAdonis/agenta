import os
import asyncio
from datetime import datetime, timezone

from pymongo import MongoClient
from bson import DBRef
from sqlalchemy import text
from sqlalchemy.dialects.postgresql import UUID
import uuid_utils.compat as uuid

# Assuming agenta_backend.models.db_models contains your SQLAlchemy models
from agenta_backend.models.db_models import (
    Base,
    UserDB,
    ImageDB,
    AppDB,
    DeploymentDB,
    VariantBaseDB,
    AppVariantDB,
    AppVariantRevisionsDB,
    AppEnvironmentDB,
    AppEnvironmentRevisionDB,
    TemplateDB,
    TestSetDB,
    EvaluatorConfigDB,
    HumanEvaluationDB,
    HumanEvaluationScenarioDB,
    EvaluationDB,
    EvaluationScenarioDB,
    IDsMappingDB,
)

from agenta_backend.migrations.mongo_to_postgres.utils import (
    drop_all_tables,
    create_all_tables,
    print_migration_report,
    store_mapping,
    get_mapped_uuid,
    generate_uuid,
    get_datetime,
    migrate_collection,
)

from agenta_backend.models.shared_models import TemplateType

tables = [
    UserDB,
    ImageDB,
    AppDB,
    DeploymentDB,
    VariantBaseDB,
    AppVariantDB,
    AppVariantRevisionsDB,
    AppEnvironmentDB,
    AppEnvironmentRevisionDB,
    TemplateDB,
    TestSetDB,
    EvaluatorConfigDB,
    HumanEvaluationDB,
    HumanEvaluationScenarioDB,
    EvaluationDB,
    EvaluationScenarioDB,
    IDsMappingDB,
]


async def transform_user(user):
    user_uuid = generate_uuid()
    await store_mapping("users", user["_id"], user_uuid)
    return {
        "id": user_uuid,
        "uid": user["uid"],
        "username": user["username"],
        "email": user["email"],
        "created_at": get_datetime(user.get("created_at")),
        "updated_at": get_datetime(user.get("updated_at")),
    }


async def transform_image(image):
    user_uuid = await get_mapped_uuid(
        image["user"].id if isinstance(image["user"], DBRef) else image["user"]
    )
    image_uuid = generate_uuid()
    await store_mapping("docker_images", image["_id"], image_uuid)
    return {
        "id": image_uuid,
        "type": image["type"],
        "template_uri": image.get("template_uri"),
        "docker_id": image.get("docker_id"),
        "tags": image.get("tags"),
        "deletable": image.get("deletable", True),
        "user_id": user_uuid,
        "created_at": get_datetime(image.get("created_at")),
        "updated_at": get_datetime(image.get("updated_at")),
    }


async def transform_app(app):
    user_uuid = await get_mapped_uuid(app["user"].id)
    app_uuid = generate_uuid()
    await store_mapping("app_db", app["_id"], app_uuid)
    return {
        "id": app_uuid,
        "app_name": app["app_name"],
        "user_id": user_uuid,
        "created_at": get_datetime(app.get("created_at")),
        "updated_at": get_datetime(app.get("updated_at")),
    }


async def transform_deployment(deployment):
    app_uuid = await get_mapped_uuid(deployment["app"].id)
    user_uuid = await get_mapped_uuid(deployment["user"].id)
    deployment_uuid = generate_uuid()
    await store_mapping("deployments", deployment["_id"], deployment_uuid)
    return {
        "id": deployment_uuid,
        "app_id": app_uuid,
        "user_id": user_uuid,
        "container_name": deployment.get("container_name"),
        "container_id": deployment.get("container_id"),
        "uri": deployment.get("uri"),
        "status": deployment["status"],
        "created_at": get_datetime(deployment.get("created_at")),
        "updated_at": get_datetime(deployment.get("updated_at")),
    }


async def transform_variant_base(base):
    app_uuid = await get_mapped_uuid(base["app"].id)
    user_uuid = await get_mapped_uuid(base["user"].id)
    image_uuid = await get_mapped_uuid(base["image"].id)
    deployment_uuid = base["deployment"] and await get_mapped_uuid(base["deployment"])
    base_uuid = generate_uuid()
    await store_mapping("bases", base["_id"], base_uuid)
    return {
        "id": base_uuid,
        "app_id": app_uuid,
        "user_id": user_uuid,
        "base_name": base["base_name"],
        "image_id": image_uuid,
        "deployment_id": deployment_uuid,
        "created_at": get_datetime(base.get("created_at")),
        "updated_at": get_datetime(base.get("updated_at")),
    }


async def transform_app_variant(variant):
    app_uuid = await get_mapped_uuid(variant["app"].id)
    image_uuid = await get_mapped_uuid(variant["image"].id)
    user_uuid = await get_mapped_uuid(variant["user"].id)
    modified_by_uuid = await get_mapped_uuid(variant["modified_by"].id)
    base_uuid = await get_mapped_uuid(variant["base"].id)
    variant_uuid = generate_uuid()
    await store_mapping("app_variants", variant["_id"], variant_uuid)
    return {
        "id": variant_uuid,
        "app_id": app_uuid,
        "variant_name": variant["variant_name"],
        "revision": variant["revision"],
        "image_id": image_uuid,
        "user_id": user_uuid,
        "modified_by_id": modified_by_uuid,
        "base_name": variant.get("base_name"),
        "base_id": base_uuid,
        "config_name": variant["config_name"],
        "config_parameters": variant["config"],
        "created_at": get_datetime(variant.get("created_at")),
        "updated_at": get_datetime(variant.get("updated_at")),
    }


async def transform_app_variant_revision(revision):
    variant_uuid = await get_mapped_uuid(revision["variant"].id)
    modified_by_uuid = await get_mapped_uuid(revision["modified_by"].id)
    base_uuid = await get_mapped_uuid(revision["base"].id)
    revision_uuid = generate_uuid()
    await store_mapping("app_variant_revisions", revision["_id"], revision_uuid)
    return {
        "id": revision_uuid,
        "variant_id": variant_uuid,
        "revision": revision["revision"],
        "modified_by_id": modified_by_uuid,
        "base_id": base_uuid,
        "config_name": revision["config"]["config_name"],
        "config_parameters": revision["config"]["parameters"],
        "created_at": get_datetime(revision["created_at"]),
        "updated_at": get_datetime(revision["updated_at"]),
    }


async def transform_app_environment(environment):
    app_uuid = await get_mapped_uuid(environment["app"].id)
    user_uuid = await get_mapped_uuid(environment["user"].id)
    variant_uuid = await get_mapped_uuid(environment["deployed_app_variant"])
    revision_uuid = await get_mapped_uuid(environment["deployed_app_variant_revision"])
    deployment_uuid = await get_mapped_uuid(environment["deployment"])
    environment_uuid = generate_uuid()
    await store_mapping("environments", environment["_id"], environment_uuid)
    return {
        "id": environment_uuid,
        "app_id": app_uuid,
        "name": environment["name"],
        "user_id": user_uuid,
        "revision": environment["revision"],
        "deployed_app_variant_id": variant_uuid,
        "deployed_app_variant_revision_id": revision_uuid,
        "deployment_id": deployment_uuid,
        "created_at": get_datetime(environment.get("created_at")),
    }


async def transform_app_environment_revision(revision):
    environment_uuid = await get_mapped_uuid(revision["environment"].id)
    modified_by_uuid = await get_mapped_uuid(revision["modified_by"].id)
    variant_revision_uuid = await get_mapped_uuid(
        revision["deployed_app_variant_revision"]
    )
    deployment_uuid = await get_mapped_uuid(revision["deployment"])
    revision_uuid = generate_uuid()
    await store_mapping("environments_revisions", revision["_id"], revision_uuid)
    return {
        "id": revision_uuid,
        "environment_id": environment_uuid,
        "revision": revision["revision"],
        "modified_by_id": modified_by_uuid,
        "deployed_app_variant_revision_id": variant_revision_uuid,
        "deployment_id": deployment_uuid,
        "created_at": get_datetime(revision["created_at"]),
    }


async def transform_template(template):
    template_uuid = generate_uuid()
    await store_mapping("templates", template["_id"], template_uuid)

    # Ensure type is correctly mapped to TemplateType enum
    template_type = (
        TemplateType(template["type"]) if "type" in template else TemplateType.IMAGE
    )

    return {
        "id": template_uuid,
        "type": template_type,
        "template_uri": template.get("template_uri"),
        "tag_id": template.get("tag_id"),
        "name": template["name"],
        "repo_name": template.get("repo_name"),
        "title": template["title"],
        "description": template["description"],
        "size": template.get("size"),
        "digest": template.get("digest"),
        "last_pushed": get_datetime(template.get("last_pushed")),
    }


async def transform_test_set(test_set):
    app_uuid = await get_mapped_uuid(test_set["app"].id)
    user_uuid = await get_mapped_uuid(test_set["user"].id)
    test_set_uuid = generate_uuid()
    await store_mapping("testsets", test_set["_id"], test_set_uuid)
    return {
        "id": test_set_uuid,
        "name": test_set["name"],
        "app_id": app_uuid,
        "csvdata": test_set["csvdata"],
        "user_id": user_uuid,
        "created_at": get_datetime(test_set.get("created_at")),
        "updated_at": get_datetime(test_set.get("updated_at")),
    }


async def transform_evaluator_config(config):
    evaluation_uuid = await get_mapped_uuid(config["evaluation"].id)
    scenario_uuid = await get_mapped_uuid(config["evaluation_scenario"].id)
    app_uuid = await get_mapped_uuid(config["app"].id)
    user_uuid = await get_mapped_uuid(config["user"].id)
    config_uuid = generate_uuid()
    await store_mapping("evaluators_configs", config["_id"], config_uuid)
    return {
        "id": config_uuid,
        "evaluation_id": evaluation_uuid,
        "evaluation_scenario_id": scenario_uuid,
        "app_id": app_uuid,
        "user_id": user_uuid,
        "name": config["name"],
        "evaluator_key": config["evaluator_key"],
        "settings_values": config["settings_values"],
        "created_at": get_datetime(config.get("created_at")),
        "updated_at": get_datetime(config.get("updated_at")),
    }


async def transform_human_evaluation(evaluation):
    app_uuid = await get_mapped_uuid(evaluation["app"].id)
    user_uuid = await get_mapped_uuid(evaluation["user"].id)
    test_set_uuid = await get_mapped_uuid(evaluation["testset"].id)
    variant_uuid = await get_mapped_uuid(evaluation["variants"][0])
    revision_uuid = await get_mapped_uuid(evaluation["variants_revisions"][0])
    evaluation_uuid = generate_uuid()
    await store_mapping("human_evaluations", evaluation["_id"], evaluation_uuid)
    return {
        "id": evaluation_uuid,
        "app_id": app_uuid,
        "user_id": user_uuid,
        "status": evaluation["status"],
        "evaluation_type": evaluation["evaluation_type"],
        "variant_id": variant_uuid,
        "variant_revision_id": revision_uuid,
        "testset_id": test_set_uuid,
        "created_at": get_datetime(evaluation.get("created_at")),
        "updated_at": get_datetime(evaluation.get("updated_at")),
    }


async def transform_human_evaluation_scenario(scenario):
    user_uuid = await get_mapped_uuid(scenario["user"].id)
    evaluation_uuid = await get_mapped_uuid(scenario["evaluation"].id)
    scenario_uuid = generate_uuid()
    await store_mapping("human_evaluations_scenarios", scenario["_id"], scenario_uuid)
    return {
        "id": scenario_uuid,
        "user_id": user_uuid,
        "evaluation_id": evaluation_uuid,
        "inputs": scenario["inputs"],
        "outputs": scenario["outputs"],
        "vote": scenario.get("vote"),
        "score": scenario.get("score"),
        "correct_answer": scenario.get("correct_answer"),
        "created_at": get_datetime(scenario.get("created_at")),
        "updated_at": get_datetime(scenario.get("updated_at")),
        "is_pinned": scenario.get("is_pinned"),
        "note": scenario.get("note"),
    }


async def transform_evaluation(evaluation):
    app_uuid = await get_mapped_uuid(evaluation["app"].id)
    user_uuid = await get_mapped_uuid(evaluation["user"].id)
    test_set_uuid = await get_mapped_uuid(evaluation["testset"].id)
    variant_uuid = await get_mapped_uuid(evaluation["variant"])
    revision_uuid = await get_mapped_uuid(evaluation["variant_revision"])
    evaluation_uuid = generate_uuid()
    await store_mapping("evaluations", evaluation["_id"], evaluation_uuid)
    return {
        "id": evaluation_uuid,
        "app_id": app_uuid,
        "user_id": user_uuid,
        "status": evaluation["status"],
        "testset_id": test_set_uuid,
        "variant_id": variant_uuid,
        "variant_revision_id": revision_uuid,
        "aggregated_results": evaluation["aggregated_results"],
        "average_cost": evaluation["average_cost"],
        "total_cost": evaluation["total_cost"],
        "average_latency": evaluation["average_latency"],
        "created_at": get_datetime(evaluation.get("created_at")),
        "updated_at": get_datetime(evaluation.get("updated_at")),
    }


async def transform_evaluation_scenario(scenario):
    user_uuid = await get_mapped_uuid(scenario["user"].id)
    evaluation_uuid = await get_mapped_uuid(scenario["evaluation"].id)
    variant_uuid = await get_mapped_uuid(scenario["variant_id"])
    scenario_uuid = generate_uuid()
    await store_mapping("evaluation_scenarios", scenario["_id"], scenario_uuid)
    return {
        "id": scenario_uuid,
        "user_id": user_uuid,
        "evaluation_id": evaluation_uuid,
        "variant_id": variant_uuid,
        "inputs": scenario["inputs"],
        "outputs": scenario["outputs"],
        "correct_answers": scenario.get("correct_answers"),
        "is_pinned": scenario.get("is_pinned"),
        "note": scenario.get("note"),
        "results": scenario["results"],
        "latency": scenario.get("latency"),
        "cost": scenario.get("cost"),
        "created_at": get_datetime(scenario.get("created_at")),
        "updated_at": get_datetime(scenario.get("updated_at")),
    }


async def main():
    try:
        await drop_all_tables()
        await create_all_tables(tables=tables)
        await migrate_collection("users", UserDB, transform_user)
        await migrate_collection("docker_images", ImageDB, transform_image)
        await migrate_collection("app_db", AppDB, transform_app)
        await migrate_collection("deployments", DeploymentDB, transform_deployment)
        await migrate_collection("bases", VariantBaseDB, transform_variant_base)
        await migrate_collection("app_variants", AppVariantDB, transform_app_variant)
        await migrate_collection(
            "app_variant_revisions",
            AppVariantRevisionsDB,
            transform_app_variant_revision,
        )
        await migrate_collection(
            "environments", AppEnvironmentDB, transform_app_environment
        )
        await migrate_collection(
            "environments_revisions",
            AppEnvironmentRevisionDB,
            transform_app_environment_revision,
        )
        await migrate_collection("templates", TemplateDB, transform_template)
        await migrate_collection("testsets", TestSetDB, transform_test_set)
        await migrate_collection(
            "evaluators_configs", EvaluatorConfigDB, transform_evaluator_config
        )
        await migrate_collection(
            "human_evaluations", HumanEvaluationDB, transform_human_evaluation
        )
        await migrate_collection(
            "human_evaluations_scenarios",
            HumanEvaluationScenarioDB,
            transform_human_evaluation_scenario,
        )
        await migrate_collection("evaluations", EvaluationDB, transform_evaluation)
        await migrate_collection(
            "evaluation_scenarios", EvaluationScenarioDB, transform_evaluation_scenario
        )
        print("Migration completed successfully.")
    except Exception as e:
        print(f"\n====================== Error ======================\n")
        print(f"Error occurred: {e}")
    finally:
        print_migration_report()


if __name__ == "__main__":
    asyncio.run(main())
