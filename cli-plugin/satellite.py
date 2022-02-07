# Copyright 2022 Nokia
# Licensed under the BSD 3-Clause License.
# SPDX-License-Identifier: BSD-3-Clause

###########################################################################
# Description: CLI plugin for the command 'show satellite'
###########################################################################

from srlinux.mgmt.cli import CliPlugin
from srlinux.syntax import Syntax
from srlinux.schema import FixedSchemaRoot
from srlinux.location import build_path
from srlinux.mgmt.cli import KeyCompleter
from srlinux import strings
from srlinux.data import ColumnFormatter, TagValueFormatter, TagValueWithKeyLineFormatter, Formatter
from srlinux.data import Border, Borders, Data, Indent, Header, Whiteline, Footer, Alignment
from srlinux.syntax.value_checkers import IntegerValueInRangeChecker
from srlinux.data.utilities import Percentage
import json

class Plugin(CliPlugin):

    '''
    Load() method: load new CLI command at CLI startup
    In: cli, the root node of the CLI command hierachy
    '''
    def load(self, cli, **_kwargs):
        syntax = Syntax('satellite', help='Display all satellite statistics')

        print("Loading CLI:", syntax)

        cli.show_mode.add_command(
                syntax,
                update_location=False,
                callback=self._print,
                schema=self._my_schema()
                )

    '''
    _my_schema() method: contruct schema for this CLI command
    Return: schema object
    '''
    def _my_schema(self):
        root = FixedSchemaRoot()

        satellite = root.add_child(
                'satellite',
                fields=['Name','ID','Timestamp','Latitude','Longitude','Altitude','Velocity','Visibility','Footprint','Daynum','Solar-lat','Solar-lon','Units'])

        return root

    '''
    _fetch_state() method: extract relevant data from the state datastore
    In: state, reference to the datastores
    In: arguments, the CLI command's context
    Return: copy of a section of the state datastore
    '''
    def _fetch_state(self, state, arguments):
        ## build a YANG path objects from the path string
        ## retrieve the interface name from the arguments
        path = build_path('/satellite')

        ## fetch the value of the YANG path recursively
        ## this will return everythin under the given interface
        data = state.server_data_store.get_data(path, recursive=True)

        return data


    '''
    _populate_schema() method: fill in schema from state datastore
    In: state_datastore, state datastore extract
    In: arguments, the CLI commands context
    Return: filled-in schema
    '''
    def _populate_schema(self, state_datastore, arguments):
        #retrieve the schema from the input arguments
        schema = Data(arguments.schema)

        #populate it with the relevant data from the state datastore
        for satellite in state_datastore.satellite.items():
            node = schema.satellite.create()
            node.name = satellite.name
            node.id = satellite.id
            node.timestamp = satellite.timestamp
            node.latitude = satellite.latitude
            node.longitude = satellite.longitude
            node.altitude = satellite.altitude
            node.velocity = satellite.velocity
            node.visibility = satellite.visibility
            node.footprint = satellite.footprint
            node.daynum = satellite.daynum
            node.solar_lat = satellite.solar_lat
            node.solar_lon = satellite.solar_lon
            node.units = satellite.units

        return schema

    '''
    _set_formatters() method
    In: schema, schema to augment with formatters
    '''
    def _set_formatters(self, schema):
        #schema.set_formatter('/satellite',Border(TagValueFormatter(), Border.Above | Border.Below))
        schema.set_formatter('/satellite',Border(WorldMapFormatter(), Border.Above | Border.Below, '='))


    '''
    _print() method: the callback function
    In: state, reference to the datastores
    In: arguments, the CLI command's context
    In: output: the CLI output object
    '''
    def _print(self, state, arguments, output, **_kwargs):
        state_datastore = self._fetch_state(state, arguments)

        #print('child_names', *state_datastore.child_names)
        #for child in state_datastore.iter_children():
        #    if 'satellite' in str(child):
        #        print("child", child)
        #        for field, value in zip(child.field_names, child.field_values):
        #            print(f"    {field} = {value}")

        schema = self._populate_schema(state_datastore, arguments)
        self._set_formatters(schema)
        output.print_data(schema)

######################################################################
#
# Custom formatter 'WorldMapFormatter'
#
######################################################################
class WorldMapFormatter(Formatter):

    worldmap_list = [
        "|                                                                       |",
        "|          . _..::__:  ,-\"-\"._        |]       ,     _,.__              |",
        "|  _.___ _ _<_>`!(._`.`-.    /         _._     `_ ,_/  '  '-._.---.-.__ |",
        "|.{     \" \"  -==,',._\{  \  /  {) _   / _ \">_,-' `                 /-/_ |",
        "|\_.:--.        ._ )`^-.  \"'     / ( [_/(                        __,/-' |",
        "|'\"'    \        \"    _\         -_,--'                        /. (|    |",
        "|       |           ,'          _)_.\\\._ <> {}             _,' /  '     |",
        "|       `.         /           [_/_'   \"(                <'}  )         |",
        "|        \\\    .-. )           /   `-'\"..' `:._          _)  '          |",
        "|          \  (   `(          /         `:\  > \  ,-^.  /' '            |",
        "|           `._,   \"\"         |           \`'   \|   ?_)  {\            |",
        "|               =.---.        `._._       ,'     \"`  |' ,- '.           |",
        "|                |    `-._         |     /          `:`<_|=--._         |",
        "|                (        >        .     | ,          `=.__.`-'\        |",
        "|                  .     /         |     |{|               ,-.,\        |",
        "|                  |   ,'           \   / `'             ,\"     `\      |",
        "|                  |  /              |_'                 |  __   /      |",
        "|                  | |                                   '-'  `-'     \.|",
        "|                  |/                                          \"      / |",
        "|                  \.                                                '  |",
        "|                                                                       |",
        "|                   ,/           _ _____._.--._ _..---.---------.       |",
        "|__,-----\"-..?----_/ )\    . ,-'\"              \"                  (__--/|",
        "|                    /__/\/                                             |",
        "|                                                                       |"]

    def __init__(self):
        self.width = 73
        self.height = 25

        self.worldmap = [list(line.strip()) for line in self.worldmap_list]

    def _map_coordinates(self, x, in_min, in_max, out_min, out_max):
        return round((x - in_min) * (out_max - out_min) / (in_max - in_min) + out_min)


    def iter_format(self, entry, max_width):
        if entry.name:
            ## Convert lat. and lon. into 2D coordinates on the worldmap
            lat = self._map_coordinates(float(entry.latitude),90,-90,0,self.height-1)
            lon = self._map_coordinates(float(entry.longitude),-180,180,0,self.width-1)

            self.worldmap[lat][lon] = '\033[5;92m#\033[00m' ## Using ANSI escape codes to print color


            position = [1,2,3,4,5,6,7,8,9,10,11,12,13,14]

            data = [f"\tName        : {entry.name}",
                    f"\tId          : {entry.id}",
                    f"\tTimestamp   : {entry.timestamp}",
                    f"\tLatitude    : {entry.latitude}",
                    f"\tLongitude   : {entry.longitude}",
                    f"\tAltitude    : {entry.altitude}",
                    f"\tVelocity    : {entry.velocity}",
                    f"\tVisibility  : {entry.visibility}",
                    f"\tFootprint   : {entry.footprint}",
                    f"\tDaynum      : {entry.daynum}",
                    f"\tSolar lat.  : {entry.solar_lat}",
                    f"\tSolar lon.  : {entry.solar_lon}",
                    f"\tUnits       : {entry.units}",
                    f"\tCharacter   : \033[92m'#'\033[00m"]

            for i, row in enumerate(self.worldmap):
                if i in position:
                    line = "".join(row) + data[position.index(i)]
                else:
                    line = "".join(row)
                yield line
        else:
            position = [1,2]

            data = [f"\tWe have lost connection to the space station",
                    f"\tPlease contact your local astronaut!"]

            for i, row in enumerate(self.worldmap):
                if i in position:
                    line = "".join(row) + data[position.index(i)]
                else:
                    line = "".join(row)
                yield line
