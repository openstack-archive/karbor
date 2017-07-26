================================
Data Protection service overview
================================

Karbor responsibility is protecting the Data and Meta-Data that comprises an
OpenStack-deployed Application against loss/damage (e.g. backup, replication)
- not to be confused with Application Security or DLP. It does that by providing
a standard framework of APIs and services that enables vendors to introduce various data
protection services into a coherent and unified flow for the user.

OpenStack Data Protection Orchestration includes the following components:

karbor-api
  Accepts API calls for provider, plan, checkpoint, scheduled operations,
  triggers, protectables, and restores.

karbor-protection
  Responsible for orchestrating basic operations (protect, restore, delete)
  over multiple resources.

karbor-operationengine
  Responsible for composing basic operations, scheduling operations, and
  tracking their progress.

