from django.db import transaction
from huey.contrib.djhuey import db_periodic_task, lock_task

from Harvest.huey_scheduler import IntervalSeconds
from Harvest.utils import get_logger
from monitoring.decorators import update_component_status
from torrents.alcazar_client import AlcazarClient
from torrents.alcazar_event_processor import AlcazarEventProcessor
from torrents.exceptions import AlcazarNotConfiguredException

logger = get_logger(__name__)

UPDATE_BATCH_SIZE = 10000


@db_periodic_task(IntervalSeconds(3))
@transaction.atomic
@lock_task('poll_alcazar')
@update_component_status(
    'alcazar_update',
    'Alcazar update completed successfully in {time_taken:.3f} s.',
    'Alcazar update crashed.',
)
def poll_alcazar():
    try:
        client = AlcazarClient(timeout=60)
    except AlcazarNotConfiguredException:
        logger.info('Skipping alcazar poll due to missing config.')
        return

    update_batch = client.pop_update_batch(10000)

    num_added = 0
    num_updated = 0
    num_removed = 0

    for realm_batch in update_batch.values():
        num_added += len(realm_batch['added'])
        num_updated += len(realm_batch['updated'])
        num_removed += len(realm_batch['removed'])

    logger.debug('Received {} added, {} updated and {} removed from alcazar.', num_added, num_updated, num_removed)

    processor = AlcazarEventProcessor()
    processor.process(update_batch)
