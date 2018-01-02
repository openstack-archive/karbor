#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

from oslo_config import cfg

time_trigger_opts = [
    cfg.IntOpt('min_interval',
               default=60 * 60,
               help='The minimum interval of two adjacent time points. '
                    'min_interval >= (max_window_time * 2)'),

    cfg.IntOpt('min_window_time',
               default=900,
               help='The minimum window time'),

    cfg.IntOpt('max_window_time',
               default=1800,
               help='The maximum window time'),

    cfg.StrOpt('time_format',
               default='calendar',
               choices=['crontab', 'calendar'],
               help='The type of time format which is used to compute time'),

    cfg.IntOpt('trigger_poll_interval',
               default=15,
               help='Interval, in seconds, in which Karbor will poll for '
                    'trigger events'),

    cfg.StrOpt('scheduling_strategy',
               default='multi_node',
               help='Time trigger scheduling strategy '
               )
]

CONF = cfg.CONF
CONF.register_opts(time_trigger_opts)
