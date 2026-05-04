_Please :star: this repo if you find it useful_

# EMT Madrid bus and bicimad platform for Home Assistant

This is a custom integration for Home Assistant that allows you to have the waiting time for a specific Madrid-EMT bus stop. Each sensor will provide the arrival time for the next 2 buses of the line specified in the configuration.
The integration also provides sensors to track the free docks and available bikes in BiciMad stations.

Thanks to [EMT Madrid MobilityLabs](https://mobilitylabs.emtmadrid.es/) for providing the data and [documentation](https://apidocs.emtmadrid.es/).

![Example](example.png)
![Example attributes](example_attributes.png)

## Prerequisites

To use the EMT Mobilitylabs API you need to register in their [website](https://mobilitylabs.emtmadrid.es/). You have to provide a valid email account and a password that will be used to configure the sensor. Once you are registered you will receive a confirmation email to activate your account. It will not work until you have completed all the steps.

## Installation

### HACS installation

1. Open Home Assistant and go to HACS (Home Assistant Community Store).
2. In HACS, go to the "Integrations" tab and click on the three dots in the top right corner.
3. Select "Custom repositories" and enter the repository URL: `https://github.com/fermartv/emt_madrid`.
4. Select the category as "Integration" and click "Add."
5. Once the repository is added, search for "EMT Madrid" in HACS and click "Install."
6. Restart Home Assistant.


### Manual installation

1. Using the tool of choice open the directory for your HA configuration (where you find `configuration.yaml`).
2. If you do not have a `custom_components` directory there, you need to create it.
3. Download _all_ the files from the `custom_components/emt_madrid` directory in this repository.
4. Place the files you downloaded in the new directory you created.
5. Restart Home Assistant

## Configuration

This integration is configured entirely through the Home Assistant UI (no `configuration.yaml` needed).

1. Go to **Settings** → **Devices & Services** → **Add Integration**
2. Search for **EMT Madrid** and select it
3. Enter your EMT MobilityLabs **email** and **password**
4. Select the type of sensor you want to create:
   - **Bus (EMT)**: Monitor bus arrival times at a stop
   - **BiciMad**: Monitor available bikes at a station
5. Enter the **Stop ID** or **Station ID** (and optionally specify bus lines)
6. Click **Submit**

To add more stops/stations, repeat the process — each stop/station is added as a separate entry.

## Bus Sensors

### Sensors, status and attributes

Once configured, you will have one sensor per line specified. If no lines are provided, it will create a sensor for each line at that stop ID. The name of the sensor will be automatically generated: `Bus {line} - {stop_name}`. All sensors update every minute.

**state**:\
 _(int)_\
 Arrival time in minutes for the next bus. It will show "unknown" when there are no more buses coming and 45 when the arrival time is over 45 minutes.

### Attributes

**next_bus**: _(int)_ Arrival time in minutes for the second bus.

**stop_id**: _(int)_ Bus stop ID given in the configuration.

**stop_name**: _(string)_ Bus stop name from EMT.

**stop_address**: _(string)_ Bus stop address from EMT.

**line**: _(string)_ Bus line.

**destination**: _(string)_ Bus line last stop.

**origin**: _(string)_ Bus line first stop.

**start_time**: _(string)_ Time at which the first bus leaves the first stop.

**end_time**: _(string)_ Time at which the last bus leaves the first stop.

**max_frequency**: _(int)_ Maximum frequency for this line.

**min_frequency**: _(int)_ Minimum frequency for this line.

**distance**: _(int)_ Distance (in metres) from the next bus to the stop.

### Getting the Stop ID

You can find the bus stop ID using the EMT MobilityLabs API or by inspecting the EMT website.

### Second bus sensor

If you want a specific sensor for the second bus arrival time, use a template sensor:

```yaml
template:
  - sensor:
      - name: "Siguiente bus 27"
        unit_of_measurement: "min"
        state: "{{ state_attr('sensor.bus_27_cibeles_casa_de_america', 'next_bus') }}"
```

## BiciMad Sensors

### Attributes

**station_id**: _(int)_ Station ID given in the configuration.

**station_number**: _(int)_ Station number as shown in BiciMad App.

**station_name**: _(string)_ Station name from EMT.

**station_address**: _(string)_ Station address from EMT.

**free_bases**: _(int)_ Number of free bases to dock bikes into.

**bikes**: _(int)_ Number of available bikes in the station.

**station_coordinates**: _(list)_ Geographic coordinates of the station.

### Getting the Station ID

The station ID can be obtained from the [BiciMad website](https://www.bicimad.com/mapa). When you click on a station, the URL will contain the station ID.

![Example attributes](obtain_bicimad_station-id.png)

## Roadmap

1. Move to fully async HTTP client (aiohttp).
2. Add Spanish translations for the config flow.
