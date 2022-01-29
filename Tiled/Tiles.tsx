<?xml version="1.0" encoding="UTF-8"?>
<tileset version="1.5" tiledversion="1.7.2" name="Tiles" tilewidth="48" tileheight="48" tilecount="100" columns="10">
 <image source="Tiles.png" trans="ffffff" width="480" height="480"/>
 <tile id="0">
  <properties>
   <property name="can_move_east" type="bool" value="true"/>
   <property name="can_move_north" type="bool" value="false"/>
   <property name="can_move_south" type="bool" value="true"/>
   <property name="can_move_west" type="bool" value="true"/>
   <property name="floor" type="bool" value="true"/>
  </properties>
 </tile>
 <tile id="1">
  <properties>
   <property name="can_move_east" type="bool" value="true"/>
   <property name="can_move_north" type="bool" value="true"/>
   <property name="can_move_south" type="bool" value="false"/>
   <property name="can_move_west" type="bool" value="true"/>
   <property name="floor" type="bool" value="true"/>
  </properties>
 </tile>
 <tile id="2">
  <properties>
   <property name="can_move_east" type="bool" value="false"/>
   <property name="can_move_north" type="bool" value="true"/>
   <property name="can_move_south" type="bool" value="true"/>
   <property name="can_move_west" type="bool" value="true"/>
   <property name="floor" type="bool" value="true"/>
  </properties>
 </tile>
 <tile id="3">
  <properties>
   <property name="can_move_east" type="bool" value="true"/>
   <property name="can_move_north" type="bool" value="true"/>
   <property name="can_move_south" type="bool" value="true"/>
   <property name="can_move_west" type="bool" value="false"/>
   <property name="floor" type="bool" value="true"/>
  </properties>
 </tile>
</tileset>
