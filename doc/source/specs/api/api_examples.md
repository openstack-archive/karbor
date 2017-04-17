# Karbor API #

----------

## Protection Provider ##

### List Protection Providers ###

> **get** : /v1/{project_id}/providers

#### Response JSON ####
```json
{
  "providers": [
    {
      "id": "2220f8b1-975d-4621-a872-fa9afb43cb6c",
      "name": "OS Infra Provider",
      "description": "This provider uses OpenStack's own services (swift, cinder) as storage",
      "extended_info_schema": {
        "options_schema": {
          "OS::Cinder::Volume": {
            "required": [
              "backup_mode"
            ],
            "type": "object",
            "properties": {
              "backup_mode": {
                "default": "auto",
                "enum": [
                  "full",
                  "incremental",
                  "auto"
                ],
                "type": "string",
                "description": "The backup mode.",
                "title": "Backup Mode"
              }
            },
            "title": "Cinder Protection Options"
          }
        },
        "saved_info_schema": {
          "OS::Cinder::Volume": {
            "required": [
              "name"
            ],
            "type": "object",
            "properties": {
              "name": {
                "type": "string",
                "description": "The name for this backup.",
                "title": "Name"
              }
            },
            "title": "Cinder Protection Saved Info"
          }
        },
        "restore_schema": {
          "OS::Cinder::Volume": {
            "type": "object",
            "properties": {
              "restore_name": {
                "type": "string",
                "description": "The name of the restored volume.",
                "title": "Restore Name"
              }
            },
            "title": "Cinder Protection Restore"
          }
        }
      }
    }
  ],
  "providers_links": [
    {
      "href": "/v1/{project_id}/providers?limit={limit_num}&marker=cf56bd3e-97a7-4078-b6d5-f36246333fd9",
      "rel": "next"
    }
  ]
}
```

### Show Protection Provider ###
> **get** : /v1/{project_id}/providers/{provider_id}
#### Response JSON ####
```json
{
  "provider": {
    "id": "2220f8b1-975d-4621-a872-fa9afb43cb6c",
    "name": "OS Infra Provider",
    "description": "This provider uses OpenStack's own services (swift, cinder) as storage",
    "extended_info_schema": {
      "options_schema": {
        "OS::Cinder::Volume": {
          "required": [
            "backup_mode"
          ],
          "type": "object",
          "properties": {
            "backup_mode": {
              "default": "auto",
              "enum": [
                "full",
                "incremental",
                "auto"
              ],
              "type": "string",
              "description": "The backup mode.",
              "title": "Backup Mode"
            }
          },
          "title": "Cinder Protection Options"
        }
      },
      "saved_info_schema": {
        "OS::Cinder::Volume": {
          "required": [
            "name"
          ],
          "type": "object",
          "properties": {
            "name": {
              "type": "string",
              "description": "The name for this backup.",
              "title": "Name"
            }
          },
          "title": "Cinder Protection Saved Info"
        }
      },
      "restore_schema": {
        "OS::Cinder::Volume": {
          "type": "object",
          "properties": {
            "restore_name": {
              "type": "string",
              "description": "The name of the restored volume.",
              "title": "Restore Name"
            }
          },
          "title": "Cinder Protection Restore"
        }
      }
    }
  }
}
```

----------

## Checkpoint ##

### List Checkpoints ###
> **get** : /v1/{project_id}/providers/{provider_id}/checkpoints
#### Response JSON ####
```json
{
  "checkpoints": [
    {
      "id": "dcb20606-ad71-40a3-80e4-ef0fafdad0c3",
      "project_id": "e486a2f49695423ca9c47e589b948108",
      "status": "available",
      "protection_plan": {
        "id": "3523a271-68aa-42f5-b9ba-56e5200a2ebb",
        "name": "My 3 tier application",
        "provider_id": "cf56bd3e-97a7-4078-b6d5-f36246333fd9",
        "resources": [
          {
            "id": "99777fdd-8a5b-45ab-ba2c-52420008103f",
            "type": "OS::Glance::Image",
            "name": "cirros-0.3.4-x86_64-uec"
          },
          {
            "id": "cb4ef2ff-10f5-46c9-bce4-cf7a49c65a01",
            "type": "OS::Nova::Server",
            "name": "App server"
          },
          {
            "id": "25336116-f38e-4c22-81ad-e9b7bd71ba51",
            "type": "OS::Cinder::Volume",
            "name": "System volume"
          },
          {
            "id": "33b6bb0b-1157-4e66-8553-1c9e14b1c7ba",
            "type": "OS::Cinder::Volume",
            "name": "Data volume"
          }
        ]
      },
      "resource_graph": "[{'0x3': ['OS::Cinder::Volume', '33b6bb0b-1157-4e66-8553-1c9e14b1c7ba', 'Data volume'], '0x2': ['OS::Cinder::Volume', '25336116-f38e-4c22-81ad-e9b7bd71ba51', 'System volume'], '0x1': ['OS::Nova::Server', 'cb4ef2ff-10f5-46c9-bce4-cf7a49c65a01', 'App server'], '0x0': ['OS::Glance::Image', '99777fdd-8a5b-45ab-ba2c-52420008103f', 'cirros-0.3.4-x86_64-uec']}, [['0x1', ['0x0']]]]"
    }
  ],
  "checkpoints_links": [
    {
      "href": "/v1/{project_id}/checkpoints?limit={limit_num}&marker=dcb20606-ad71-40a3-80e4-ef0fafdad0c3",
      "rel": "next"
    }
  ]
}
```

### Create Checkpoint ###
> **post** : /v1/{project_id}/providers/{provider_id}/checkpoints
#### Request JSON ####
```json
{
  "checkpoint": {
    "plan_id": "3523a271-68aa-42f5-b9ba-56e5200a2ebb",
    "extra_info": {
      "create-by": "operation-engine",
      "trigger_id": "33b6bb0b-1157-4e66-8553-1c9e14b1c7ba",
    }
  }
}
```
#### Response JSON ####
```json
{
  "checkpoint": {
    "id": "dcb20606-ad71-40a3-80e4-ef0fafdad0c3",
    "project_id": "e486a2f49695423ca9c47e589b948108",
    "status": "available",
    "protection_plan": {
      "id": "3523a271-68aa-42f5-b9ba-56e5200a2ebb",
      "name": "My 3 tier application",
      "provider_id": "cf56bd3e-97a7-4078-b6d5-f36246333fd9",
      "resources": [
        {
          "id": "99777fdd-8a5b-45ab-ba2c-52420008103f",
          "type": "OS::Glance::Image",
          "name": "cirros-0.3.4-x86_64-uec"
        },
        {
          "id": "cb4ef2ff-10f5-46c9-bce4-cf7a49c65a01",
          "type": "OS::Nova::Server",
          "name": "App server"
        },
        {
          "id": "25336116-f38e-4c22-81ad-e9b7bd71ba51",
          "type": "OS::Cinder::Volume",
          "name": "System volume"
        },
        {
          "id": "33b6bb0b-1157-4e66-8553-1c9e14b1c7ba",
          "type": "OS::Cinder::Volume",
          "name": "Data volume"
        }
      ]
    },
    "resource_graph": "[{'0x3': ['OS::Cinder::Volume', '33b6bb0b-1157-4e66-8553-1c9e14b1c7ba', 'Data volume'], '0x2': ['OS::Cinder::Volume', '25336116-f38e-4c22-81ad-e9b7bd71ba51', 'System volume'], '0x1': ['OS::Nova::Server', 'cb4ef2ff-10f5-46c9-bce4-cf7a49c65a01', 'App server'], '0x0': ['OS::Glance::Image', '99777fdd-8a5b-45ab-ba2c-52420008103f', 'cirros-0.3.4-x86_64-uec']}, [['0x1', ['0x0']]]]"
  }
}
```

### Show Checkpoint ###
> **get** : /v1/{project_id}/providers/{provider_id}/checkpoints/{checkpoint_id}
#### Response JSON ####
```json
{
  "checkpoint": {
    "id": "dcb20606-ad71-40a3-80e4-ef0fafdad0c3",
    "project_id": "e486a2f49695423ca9c47e589b948108",
    "status": "available",
    "protection_plan": {
      "id": "3523a271-68aa-42f5-b9ba-56e5200a2ebb",
      "name": "My 3 tier application",
      "provider_id": "cf56bd3e-97a7-4078-b6d5-f36246333fd9",
      "resources": [
        {
          "id": "99777fdd-8a5b-45ab-ba2c-52420008103f",
          "type": "OS::Glance::Image",
          "name": "cirros-0.3.4-x86_64-uec"
        },
        {
          "id": "cb4ef2ff-10f5-46c9-bce4-cf7a49c65a01",
          "type": "OS::Nova::Server",
          "name": "App server"
        },
        {
          "id": "25336116-f38e-4c22-81ad-e9b7bd71ba51",
          "type": "OS::Cinder::Volume",
          "name": "System volume"
        },
        {
          "id": "33b6bb0b-1157-4e66-8553-1c9e14b1c7ba",
          "type": "OS::Cinder::Volume",
          "name": "Data volume"
        }
      ]
    },
    "resource_graph": "[{'0x3': ['OS::Cinder::Volume', '33b6bb0b-1157-4e66-8553-1c9e14b1c7ba', 'Data volume'], '0x2': ['OS::Cinder::Volume', '25336116-f38e-4c22-81ad-e9b7bd71ba51', 'System volume'], '0x1': ['OS::Nova::Server', 'cb4ef2ff-10f5-46c9-bce4-cf7a49c65a01', 'App server'], '0x0': ['OS::Glance::Image', '99777fdd-8a5b-45ab-ba2c-52420008103f', 'cirros-0.3.4-x86_64-uec']}, [['0x1', ['0x0']]]]"
  }
}
```

### Delete Checkpoint ###
> **delete** : /v1/{project_id}/providers/{provider_id}/checkpoints/{checkpoint_id}
#### Response JSON ####
```json
{}
```

----------

## Plan ##

### List Plans ###
> **get** : /v1/{project_id}/plans
#### Response JSON ####
```json
{
  "plans": [
    {
      "id": "9e5475d2-6425-4986-9136-a4f09642297f",
      "name": "My 3 tier application",
      "resources": [
        {
          "id": "99777fdd-8a5b-45ab-ba2c-52420008103f",
          "type": "OS::Glance::Image",
          "name": "cirros-0.3.4-x86_64-uec"
        },
        {
          "id": "cb4ef2ff-10f5-46c9-bce4-cf7a49c65a01",
          "type": "OS::Nova::Server",
          "name": "App server"
        },
        {
          "id": "25336116-f38e-4c22-81ad-e9b7bd71ba51",
          "type": "OS::Cinder::Volume",
          "name": "System volume",
          "extra_info": {
              "availability_zone": "az1"
          }
        },
        {
          "id": "33b6bb0b-1157-4e66-8553-1c9e14b1c7ba",
          "type": "OS::Cinder::Volume",
          "name": "Data volume",
          "extra_info": {
              "availability_zone": "az1"
          }
        }
      ],
      "status": "suspended",
      "provider_id": "cf56bd3e-97a7-4078-b6d5-f36246333fd9",
      "parameters": {
        "OS::Nova::Server": {
          "backup_name": "os"
        },
        "OS::Nova::Server#cb4ef2ff-10f5-46c9-bce4-cf7a49c65a01": {
          "backup_name": "crash"
        },
        "OS::Cinder::Volume": {
          "backup_name": "os"
        },
        "OS::Cinder::Volume#33b6bb0b-1157-4e66-8553-1c9e14b1c7ba": {
          "backup_name": "crash"
        }
      }
    }
  ],
  "plans_links": [
    {
      "href": "/v1/{project_id}/plans?limit={limit_num}&marker=9e5475d2-6425-4986-9136-a4f09642297f",
      "rel": "next"
    }
  ]
}
```

### Create Plan ###
> **post** : /v1/{project_id}/plans
#### Request JSON ####
```json
{
  "plan": {
    "name": "My 3 tier application",
    "resources": [
      {
        "id": "99777fdd-8a5b-45ab-ba2c-52420008103f",
        "type": "OS::Glance::Image",
        "name": "cirros-0.3.4-x86_64-uec"
      },
      {
        "id": "cb4ef2ff-10f5-46c9-bce4-cf7a49c65a01",
        "type": "OS::Nova::Server",
        "name": "App server"
      },
      {
        "id": "25336116-f38e-4c22-81ad-e9b7bd71ba51",
        "type": "OS::Cinder::Volume",
        "name": "System volume",
        "extra_info": {
            "availability_zone": "az1"
        }
      },
      {
        "id": "33b6bb0b-1157-4e66-8553-1c9e14b1c7ba",
        "type": "OS::Cinder::Volume",
        "name": "Data volume",
        "extra_info": {
            "availability_zone": "az1"
        }
      }
    ],
    "provider_id": "cf56bd3e-97a7-4078-b6d5-f36246333fd9",
    "parameters": {
      "OS::Nova::Server": {
        "backup_name": "os"
      },
      "OS::Nova::Server#cb4ef2ff-10f5-46c9-bce4-cf7a49c65a01": {
        "backup_name": "crash"
      },
      "OS::Cinder::Volume": {
        "backup_name": "os"
      },
      "OS::Cinder::Volume#33b6bb0b-1157-4e66-8553-1c9e14b1c7ba": {
        "backup_name": "crash"
      }
    }
  }
}
```

#### Response JSON ####
```json
{
  "plan": {
    "id": "9e5475d2-6425-4986-9136-a4f09642297f",
    "name": "My 3 tier application",
    "resources": [
      {
        "id": "99777fdd-8a5b-45ab-ba2c-52420008103f",
        "type": "OS::Glance::Image",
        "name": "cirros-0.3.4-x86_64-uec"
      },
      {
        "id": "cb4ef2ff-10f5-46c9-bce4-cf7a49c65a01",
        "type": "OS::Nova::Server",
        "name": "App server"
      },
      {
        "id": "25336116-f38e-4c22-81ad-e9b7bd71ba51",
        "type": "OS::Cinder::Volume",
        "name": "System volume",
        "extra_info": {
            "availability_zone": "az1"
        }
      },
      {
        "id": "33b6bb0b-1157-4e66-8553-1c9e14b1c7ba",
        "type": "OS::Cinder::Volume",
        "name": "Data volume",
        "extra_info": {
            "availability_zone": "az1"
        }
      }
    ],
    "status": "suspended",
    "provider_id": "cf56bd3e-97a7-4078-b6d5-f36246333fd9",
    "parameters": {
      "OS::Nova::Server": {
        "backup_name": "os"
      },
      "OS::Nova::Server#cb4ef2ff-10f5-46c9-bce4-cf7a49c65a01": {
        "backup_name": "crash"
      },
      "OS::Cinder::Volume": {
        "backup_name": "os"
      },
      "OS::Cinder::Volume#33b6bb0b-1157-4e66-8553-1c9e14b1c7ba": {
        "backup_name": "crash"
      }
    }
  }
}
```

### Show Plan ###
> **get** : /v1/{project_id}/plans/{plan_id}
#### Response JSON ####
```json
{
  "plan": {
    "id": "9e5475d2-6425-4986-9136-a4f09642297f",
    "name": "My 3 tier application",
    "resources": [
      {
        "id": "99777fdd-8a5b-45ab-ba2c-52420008103f",
        "type": "OS::Glance::Image",
        "name": "cirros-0.3.4-x86_64-uec"
      },
      {
        "id": "cb4ef2ff-10f5-46c9-bce4-cf7a49c65a01",
        "type": "OS::Nova::Server",
        "name": "App server"
      },
      {
        "id": "25336116-f38e-4c22-81ad-e9b7bd71ba51",
        "type": "OS::Cinder::Volume",
        "name": "System volume",
        "extra_info": {
            "availability_zone": "az1"
        }
      },
      {
        "id": "33b6bb0b-1157-4e66-8553-1c9e14b1c7ba",
        "type": "OS::Cinder::Volume",
        "name": "Data volume",
        "extra_info": {
            "availability_zone": "az1"
        }
      }
    ],
    "status": "suspended",
    "provider_id": "cf56bd3e-97a7-4078-b6d5-f36246333fd9",
    "parameters": {
      "OS::Nova::Server": {
        "backup_name": "os"
      },
      "OS::Nova::Server#cb4ef2ff-10f5-46c9-bce4-cf7a49c65a01": {
        "backup_name": "crash"
      },
      "OS::Cinder::Volume": {
        "backup_name": "os"
      },
      "OS::Cinder::Volume#33b6bb0b-1157-4e66-8553-1c9e14b1c7ba": {
        "backup_name": "crash"
      }
    }
  }
}
```

### Update Plan ###
> **put** : /v1/{project_id}/plans/{plan_id}
#### Request JSON ####
```json
{
  "plan":{
    "status": "started",
    "name": "My 1 tier application"
  }
}
```

#### Response JSON ####
```json
{
  "plan": {
    "id": "9e5475d2-6425-4986-9136-a4f09642297f",
    "name": "My 1 tier application",
    "resources": [
      {
        "id": "99777fdd-8a5b-45ab-ba2c-52420008103f",
        "type": "OS::Glance::Image",
        "name": "cirros-0.3.4-x86_64-uec"
      },
      {
        "id": "cb4ef2ff-10f5-46c9-bce4-cf7a49c65a01",
        "type": "OS::Nova::Server",
        "name": "App server"
      },
      {
        "id": "25336116-f38e-4c22-81ad-e9b7bd71ba51",
        "type": "OS::Cinder::Volume",
        "name": "System volume",
        "extra_info": {
            "availability_zone": "az1"
        }
      },
      {
        "id": "33b6bb0b-1157-4e66-8553-1c9e14b1c7ba",
        "type": "OS::Cinder::Volume",
        "name": "Data volume",
        "extra_info": {
            "availability_zone": "az1"
        }
      }
    ],
    "status": "started",
    "provider_id": "cf56bd3e-97a7-4078-b6d5-f36246333fd9",
    "parameters": {
      "OS::Nova::Server": {
        "backup_name": "os"
      },
      "OS::Nova::Server#cb4ef2ff-10f5-46c9-bce4-cf7a49c65a01": {
        "backup_name": "crash"
      },
      "OS::Cinder::Volume": {
        "backup_name": "os"
      },
      "OS::Cinder::Volume#33b6bb0b-1157-4e66-8553-1c9e14b1c7ba": {
        "backup_name": "crash"
      }
    }
  }
}
```

### Delete Plan ###
> **delete** : /v1/{project_id}/plans/{plan_id}
#### Response JSON ####
```json
None
```

----------

## Protectable ##

### List Protectable Types ###
> **get** : /v1/{project_id}/protectables
#### Response JSON ####
```json
{
  "protectable_type": [
    "OS::Keystone::Project",
    "OS::Cinder::Volume",
    "OS::Cinder::ConsistencyGroup",
    "OS::Glance::Image",
    "OS::Nova::Server"
  ]
}
```

### Show Protectable Type ###
> **get** : /v1/{project_id}/protectables/{protectable_type}
#### Response JSON ####
```json
{
  "protectable_type": {
    "name": "OS::Nova::Server",
    "dependent_types": [
      "OS::Cinder::Volume",
      "OS::Glance::Image"
    ]
  }
}
```

### List Protectable Instances ###
> **get** : /v1/{project_id}/protectables/{protectable_type}/instances
#### Response JSON ####
```json
{
  "instances": [
      {
          "id": "25336116-f38e-4c22-81ad-e9b7bd71ba51",
          "type": "OS::Cinder::Volume",
          "name": "System volume",
          "extra_info": {
              "availability_zone": "az1"
          }
      },
      {
          "id": "33b6bb0b-1157-4e66-8553-1c9e14b1c7ba",
          "type": "OS::Cinder::Volume",
          "name": "Data volume",
          "extra_info": {
              "availability_zone": "az1"
          }
      }
  ]
  "instances_links": [
    {
      "href": "/v1/{project_id}/instances?limit=1&marker=cb4ef2ff-10f5-46c9-bce4-cf7a49c65a01",
      "rel": "next"
    }
  ]
}
```

### Show Protectable Instance ###
> **get** : /v1/{project_id}/protectables/{protectable_type}/instances/{resource_id}
#### Response JSON ####
```json
{
  "instance": {
    "id": "cb4ef2ff-10f5-46c9-bce4-cf7a49c65a01",
    "type": "OS::Nova::Server",
    "name": "My VM",
    "dependent_resources": [
      {
        "id": "99777fdd-8a5b-45ab-ba2c-52420008103f",
        "type": "OS::Glance::Image",
        "name": "cirros-0.3.4-x86_64-uec"
      }
    ]
  }
}
```

----------

## Scheduled Operation ##

### List Scheduled Operations ###
> **get** : /v1/{project_id}/scheduled_operations
#### Response JSON ####
```json
{"operations": [
    {"scheduled_operation": {
       "id": "1a2c0c3d-f402-4cd8-b5db-82e85cb51fad",
       "name": "My scheduled operation",
       "description": "It will run everyday",
       "operation_type": "protect",
       "trigger_id": "23902b02-5666-4ee6-8dfe-962ac09c3995",
       "operation_definition": {
         "provider_id": "2a9ce1f3-cc1a-4516-9435-0ebb13caa399",
         "plan_id": "2a9ce1f3-cc1a-4516-9435-0ebb13caa398"
         },
       "enabled": 1
      }
    },
  ],
  "operations_links": ""
}
```

### Create Scheduled Operation ###
> **post** : /v1/{project_id}/scheduled_operations
#### Request JSON ####
```json
{"scheduled_operation": {
    "name": "My scheduled operation",
    "description": "It will run everyday",
    "operation_type": "protect",
    "trigger_id": "23902b02-5666-4ee6-8dfe-962ac09c3995",
    "operation_definition": {
      "provider_id": "2a9ce1f3-cc1a-4516-9435-0ebb13caa399",
      "plan_id": "2a9ce1f3-cc1a-4516-9435-0ebb13caa398"
    }
  }
}
```

#### Response JSON ####
```json
{"scheduled_operation": {
    "id": "1a2c0c3d-f402-4cd8-b5db-82e85cb51fad",
    "name": "My scheduled operation",
    "description": "It will run everyday",
    "operation_type": "protect",
    "trigger_id": "23902b02-5666-4ee6-8dfe-962ac09c3995",
    "operation_definition": {
      "provider_id": "2a9ce1f3-cc1a-4516-9435-0ebb13caa399",
      "plan_id": "2a9ce1f3-cc1a-4516-9435-0ebb13caa398"
    },
    "enabled": 1
  }
}
```

### Show Scheduled Operation ###
> **get** : /v1/{project_id}/scheduled_operations/{scheduled_operation_id}
#### Response JSON ####
```json
{"scheduled_operation": {
    "id": "1a2c0c3d-f402-4cd8-b5db-82e85cb51fad",
    "name": "My scheduled operation",
    "description": "It will run everyday",
    "operation_type": "protect",
    "trigger_id": "23902b02-5666-4ee6-8dfe-962ac09c3995",
    "operation_definition": {
      "provider_id": "2a9ce1f3-cc1a-4516-9435-0ebb13caa399",
      "plan_id": "2a9ce1f3-cc1a-4516-9435-0ebb13caa398"
    },
    "enabled": 1
  }
}
```

### Delete Scheduled Operation ###
> **delete** : /v1/{project_id}/scheduled_operations/{scheduled_operation_id}
#### Response JSON ####
```json
None
```

----------

## Restores ##

### List Restores ###
> **get** : /v1/{project_id}/restores
#### Response JSON ####
```json
{
  "restores": [
    {
      "id": "22b82aa7-9179-4c71-bba2-caf5c0e68db7",
      "project_id": "e486a2f49695423ca9c47e589b948108",
      "provider_id": "cf56bd3e-97a7-4078-b6d5-f36246333fd9",
      "checkpoint_id": "dcb20606-ad71-40a3-80e4-ef0fafdad0c3",
      "restore_target": "http://192.168.1.2/identity/",
      "parameters": {
        "username": "admin",
        "password": "***"
      },
      "status": "success"
    }
  ],
  "restores_links": [
    {
      "href": "/v1/{project_id}/restores?limit={limit_num}&marker=22b82aa7-9179-4c71-bba2-caf5c0e68db7",
      "rel": "next"
    }
  ]
}
```

### Create Restore ###
> **post** : /v1/{project_id}/restores
#### Request JSON ####
```json
{
  "restore": {
    "provider_id": "cf56bd3e-97a7-4078-b6d5-f36246333fd9",
    "checkpoint_id": "dcb20606-ad71-40a3-80e4-ef0fafdad0c3",
    "restore_target": "http://192.168.1.2/identity/",
    "restore_auth": {
      "type": "password",
      "username": "admin",
      "password": "secretadmin"
    },
    "parameters": {
      "OS::Cinder::Volume": {
      },
      "OS::Nova::Server#3f8af6c6-ecea-42bd-b44c-724785bbe5ea": {
      }
    }
  }
}
```

#### Response JSON ####
```json
{
  "restore": {
    "id": "22b82aa7-9179-4c71-bba2-caf5c0e68db7",
    "project_id": "e486a2f49695423ca9c47e589b948108",
    "provider_id": "cf56bd3e-97a7-4078-b6d5-f36246333fd9",
    "checkpoint_id": "dcb20606-ad71-40a3-80e4-ef0fafdad0c3",
    "restore_target": "http://192.168.1.2/identity/v3",
    "restore_auth": {
      "type": "password",
      "username": "admin",
      "password": "***"
    },
    "parameters": {
      "OS::Cinder::Volume": {
      },
      "OS::Nova::Server#3f8af6c6-ecea-42bd-b44c-724785bbe5ea": {
      }
    },
    "status": "success"
  }
}
```

### Show Restore ###
> **get** : /v1/{project_id}/restores/{restore_id}
#### Response JSON ####
```json
{
  "restore": {
    "id": "22b82aa7-9179-4c71-bba2-caf5c0e68db7",
    "project_id": "e486a2f49695423ca9c47e589b948108",
    "provider_id": "cf56bd3e-97a7-4078-b6d5-f36246333fd9",
    "checkpoint_id": "dcb20606-ad71-40a3-80e4-ef0fafdad0c3",
    "restore_target": "http://192.168.1.2/identity/",
    "parameters": {
      "username": "admin",
      "password": "***"
    },
    "status": "success"
  }
}
```

----------

## Trigger ##

### List Triggers ###
> **get** : /v1/{project_id}/triggers
#### Response JSON ####
```json
{"triggers": [
    {"trigger_info": {
      "id": "2a9ce1f3-cc1a-4516-9435-0ebb13caa398",
      "type": "time",
      "name": "My backup trigger",
      "properties": {
        "format": "crontab",
        "pattern": "0 9 * * *",
        "start_time": "2015-12-17T08:30:00",
        "end_time": "2016-03-17T08:30:00",
        "window": "3600",
        }
      }
    },
  ],
 "triggers_links": ""  
}
```

### Create Trigger ###
> **post** : /v1/{project_id}/triggers
#### Request JSON ####
```json
{"trigger_info": {
   "name": "My backup trigger",
   "type": "time",
   "properties": {
     "format": "crontab",
     "pattern": "0 9 * * *",
     "start_time": "2015-12-17T08:30:00",
     "end_time": "2016-03-17T08:30:00",
     "window": "3600",
    }
  }
}
```

#### Response JSON ####
```json
{"trigger_info": {
   "id": "2a9ce1f3-cc1a-4516-9435-0ebb13caa398",
   "type": "time",
   "name": "My backup trigger",
   "properties": {
     "format": "crontab",
     "pattern": "0 9 * * *",
     "start_time": "2015-12-17T08:30:00",
     "end_time": "2016-03-17T08:30:00",
     "window": "3600",
    }
  }
}
```

### Update Trigger ###
> **put** : /v1/{project_id}/triggers/{trigger_id}
#### Request JSON ####
```json
{"trigger_info": {
   "properties": {
     "format": "crontab",
     "pattern": "0 10 * * *",
     "start_time": "2015-12-17T08:30:00",
     "end_time": "2016-03-17T08:30:00",
     "window": "3600",
    }
  }
}
```

#### Response JSON ####
```json
{"trigger_info": {
   "id": "2a9ce1f3-cc1a-4516-9435-0ebb13caa398",
   "type": "time",
   "name": "My backup trigger",
   "properties": {
     "format": "crontab",
     "pattern": "0 10 * * *",
     "start_time": "2015-12-17T08:30:00",
     "end_time": "2016-03-17T08:30:00",
     "window": "3600",
    }
  }
}
```

### Show Trigger ###
> **get** : /v1/{project_id}/triggers/{trigger_id}
#### Response JSON ####
```json
{"trigger_info": {
   "id": "2a9ce1f3-cc1a-4516-9435-0ebb13caa398",
   "type": "time",
   "name": "My backup trigger",
   "properties": {
     "format": "crontab",
     "pattern": "0 9 * * *",
     "start_time": "2015-12-17T08:30:00",
     "end_time": "2016-03-17T08:30:00",
     "window": "3600",
    }
  }
}
```

### Delete Trigger ###
> **delete** : /v1/{project_id}/triggers/{trigger_id}
#### Response JSON ####
```json
None
```
