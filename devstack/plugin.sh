# Devstack extras script to install Smaug

# Test if any smaug services are enabled
# is_smaug_enabled
function is_smaug_enabled {
    echo "Checking if Smaug is Enabled"
    [[ ,${ENABLED_SERVICES} =~ ,"smaug-" ]] &&  Q_ENABLE_SMAUG="False"
    Q_ENABLE_SMAUG="True"
}

function _create_smaug_conf_dir {

    # Put config files in ``SMAUG_CONF_DIR`` for everyone to find

    sudo install -d -o $STACK_USER $SMAUG_CONF_DIR

}

function configure_smaug_api {
    if is_service_enabled smaug-api ; then
        echo "Configuring Smaug API"

        cp $SMAUG_DIR/etc/smaug.conf $SMAUG_API_CONF
        cp $SMAUG_DIR/etc/api-paste.ini $SMAUG_CONF_DIR
        cp $SMAUG_DIR/etc/policy.json $SMAUG_CONF_DIR

        iniset $SMAUG_API_CONF DEFAULT debug $ENABLE_DEBUG_LOG_LEVEL
        iniset $SMAUG_API_CONF DEFAULT verbose True
        iniset $SMAUG_API_CONF DEFAULT use_syslog $SYSLOG
        echo "Configuring Smaug API Database"
        iniset $SMAUG_API_CONF database connection `database_connection_url smaug`

        setup_colorized_logging $SMAUG_API_CONF DEFAULT
        echo "Configuring Smaug API colorized"
        if is_service_enabled keystone; then

            echo "Configuring Smaug keystone Auth"
            create_smaug_cache_dir

            # Configure auth token middleware
            configure_auth_token_middleware $SMAUG_API_CONF smaug \
                $SMAUG_AUTH_CACHE_DIR

        else
            iniset $SMAUG_API_CONF DEFAULT auth_strategy noauth
        fi
    fi
}

function create_smaug_cache_dir {

    # Delete existing dir
    sudo rm -rf $SMAUG_AUTH_CACHE_DIR
    sudo mkdir -p $SMAUG_AUTH_CACHE_DIR
    sudo chown `whoami` $SMAUG_AUTH_CACHE_DIR

}

is_smaug_enabled

if [[ "$Q_ENABLE_SMAUG" == "True" ]]; then
    if [[ "$1" == "stack" && "$2" == "pre-install" ]]; then
        echo summary "Smaug pre-install"
    elif [[ "$1" == "stack" && "$2" == "install" ]]; then
        echo_summary "Installing Smaug"

        setup_package $SMAUG_DIR -e
        _create_smaug_conf_dir

    elif [[ "$1" == "stack" && "$2" == "post-config" ]]; then
        echo_summary "Configuring Smaug"

        configure_smaug_api

        echo export PYTHONPATH=\$PYTHONPATH:$SMAUG_DIR >> $RC_DIR/.localrc.auto

    elif [[ "$1" == "stack" && "$2" == "extra" ]]; then
        echo_summary "Initializing Smaug Service"
        SMAUG_BIN_DIR=$(get_python_exec_prefix)
        if is_service_enabled smaug-api; then
            run_process smaug-api "$SMAUG_BIN_DIR/smaug-api --config-file $SMAUG_API_CONF"
        fi
    fi

    if [[ "$1" == "unstack" ]]; then

        if is_service_enabled smaug-api; then
           stop_process smaug-api
        fi
    fi
fi
