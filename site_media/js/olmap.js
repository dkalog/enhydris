/* Enhydris, Copyright 2011 National Technical University of
   Athens. */
function getUrlVars() {
    var vars = {};
    var parts = window.location.href.replace(/[?&]+([^=&]+)=([^&]*)/gi,
        function(m,key,value) {
            vars[key] = decodeURI(value);
        });
    return vars;
}

Object.extend = function(destination, source) {
    for (var property in source)
        destination[property] = source[property];
    return destination;
};

var map = null;
var apopup = null;
function InvokePopup(afeature) {
    apoint = afeature.geometry.getBounds().getCenterLonLat();
    map.panTo(apoint);
    $.get("/stations/b/"+afeature.attributes["id"]+'/', {}, function(data){
        var amessage = '';
        amessage=data;
        apopup = new OpenLayers.Popup(afeature.attributes["name"], apoint, new OpenLayers.Size(190,150), amessage, true);
        apopup.setBorder("2px solid");  
        apopup.setBackgroundColor('#EEEEBB');
        map.addPopup(apopup, true);
        HideProgress('popup');
    });
}
function InvokeTooltip(atitle){
    document.getElementById("map").title = atitle;
}
function HideTooltip(atitle){
    document.getElementById("map").title = '';
}
function CreateLayer(AName, ObjectName, AFillColor, AStrokeColor){
    if(map_mode==1){
        var params = getUrlVars();
    }
    else if(map_mode==2){
        var params = {'gentity_id': agentity_id};
    }
    var labelvalue = "";
    var labeling_opts = {
            label : labelvalue, fontColor: "#504065",
            fontSize: "9px", fontFamily: "Verdana, Arial",
            fontWeight: "bold", labelAlign: "cm" 
    };
    var general_opts = {
            externalGraphic: MEDIA_URL+'images/marker.png',
            graphicWidth: 21, graphicHeight:25, graphicXOffset:-10,
            graphicYOffset: -25, fillOpacity: 1
    };
    general_opts = Object.extend(general_opts, labeling_opts);
    AURL = "/"+ObjectName+"/kml/";
    var alayer = new OpenLayers.Layer.WFS(AName, AURL, params,
    {   projection: new OpenLayers.Projection("EPSG:4326"),
        format: OpenLayers.Format.KML,
        formatOptions: { extractAttributes:true },
        styleMap: new OpenLayers.StyleMap({
            "default": new OpenLayers.Style(
                  OpenLayers.Util.applyDefaults(general_opts,
                        OpenLayers.Feature.Vector.style["default"])),
            "select": new OpenLayers.Style(
                  OpenLayers.Util.applyDefaults({
                        externalGraphic: MEDIA_URL+'images/selected_marker.png',
                        graphicWidth: 21, graphicHeight:25, graphicXOffset:-10,
                        graphicYOffset: -25, fillOpacity: 1}, 
                        OpenLayers.Feature.Vector.style["select"])),
            "temporary": new OpenLayers.Style(
                  OpenLayers.Util.applyDefaults({
                        externalGraphic: MEDIA_URL+'images/marker.png',
                        graphicWidth: 21, graphicHeight:25, graphicXOffset:-10,
                        graphicYOffset: -25, fillOpacity: 0.7}, 
                        OpenLayers.Feature.Vector.style["select"]))
        })
    } );
    alayer.events.register("loadstart", alayer,
        function() { ShowProgress(ObjectName); } );
    alayer.events.register("loadend", alayer,
        function() { HideProgress(ObjectName); } );
    alayer.events.register("loadcancel", alayer,
        function() { HideProgress(ObjectName); } );
    alayer.events.on({
        "featureselected": function(e) {
            ShowProgress('popup');
            InvokePopup(e.feature);
        },
        "featureunselected": function(e) {
            map.removePopup(apopup);
        }
    });
    return alayer;
}
var stations = CreateLayer("Σταθμοί", "stations", '#dd0022', '#990077');
var categories = [stations];
function init() {
    var options = {
        'units' :   "m",
        'numZoomLevels' :   15,
        'sphericalMercator': true,
        'maxExtent': bounds,
        'projection'    :   new OpenLayers.Projection("EPSG:9009313"),
        'displayProjection':    new OpenLayers.Projection("EPSG:4326")
    };
    map = new OpenLayers.Map('map', options);
    map.addControl(new OpenLayers.Control.ScaleLine());
    var ANavToolBar = new OpenLayers.Control.NavToolbar();
        map.addControl(ANavToolBar);
    $("div.olControlNavToolbar").css("top","14px");
    $("div.olControlNavToolbar").css("left","11px");
    pzb = new OpenLayers.Control.PanZoomBar();
    pzb.zoomWorldIcon = false;
    map.addControl(pzb);
    map.addControl(new OpenLayers.Control.MousePosition());
    map.addControl(new OpenLayers.Control.OverviewMap());
    ls = new OpenLayers.Control.LayerSwitcher();
    map.addControl(ls);
    map.addLayers(base_layers);
    map.addLayers(categories);
    ls.baseLbl.innerHTML='Base layers';
    ls.dataLbl.innerHTML='Data layers';
    var labelButton = new OpenLayers.Control.Button({ type: OpenLayers.Control.TYPE_TOGGLE,
        title: "Show labels", displayClass: "LabelButtonClass" , trigger: function(){}});  
    labelButton.events.register("activate", labelButton,
        function() { setLayersLabels(true); } );
    labelButton.events.register("deactivate", labelButton,
        function() { setLayersLabels(false); } );
    var panel = new OpenLayers.Control.Panel({displayClass: 'olControlShowLabels' });  
    panel.addControls([labelButton]);  
    panel.activateControl(labelButton);  
    map.addControl(panel); 
    var agentity_id_repr='';
    if(map_mode==2)
    {
        agentity_id_repr=agentity_id;
    }
    var getboundoptions =  {'gentity_id': agentity_id_repr}; 
    Object.extend(getboundoptions, getUrlVars());
    $.ajax({url: "/bound/", data: getboundoptions, method: 'get', 
        success: function(data){
            bounds = OpenLayers.Bounds.fromString(data);
            bounds.transform(new OpenLayers.Projection("EPSG:4326"), new
                                 OpenLayers.Projection("EPSG:900913"));
            map.zoomToExtent(bounds);
        }, 
        error: function(data){
            map.zoomToExtent(bounds);
    }});
    var SelectControl = new OpenLayers.Control.SelectFeature(categories, {
          clickout: true, togle: false, multiple: false,
          hover: false});
    var HoverControl = new OpenLayers.Control.SelectFeature(categories, {
          clickout: false, togle: false, multiple: false,
          hover: true, highlightOnly: true, renderIntent: "temporary",
          eventListeners: { beforefeaturehighlighted: function(e){},
                            featurehighlighted: function(e){InvokeTooltip(e.feature.attributes["name"])},
                            featureunhighlighted: function(e){HideTooltip(e.feature.attributes["name"])}
                          }});
    map.addControl(SelectControl);
    map.addControl(HoverControl);
    HoverControl.activate();
    SelectControl.activate();
    ANavToolBar.controls[0].events.on({
        "activate": function(){
            HoverControl.activate();
            SelectControl.activate();
        },
        "deactivate": function(){
            HoverControl.deactivate();
            SelectControl.deactivate();
        }
    });
    ANavToolBar.controls[0].activate();
}

function ShowProgress(name){
   var aprogress = document.getElementById("map_progress");
   if(aprogress==null)return;
   aprogress.innerHTML=
       "<img src='"+MEDIA_URL+"images/wait16.gif'>";
}

function HideProgress(name){
   var aprogress = document.getElementById("map_progress");
   if(aprogress==null)return;
   aprogress.innerHTML="";
}

function setLayersLabels(value){
    for(i=0;i<categories.length;i++){
        var layer = categories[i];
        var defaultStyle = layer.styleMap.styles["default"].defaultStyle;
        if(value)
            defaultStyle["label"]="${name}";
        else
            defaultStyle["label"]="";
        layer.styleMap.styles["default"].setDefaultStyle(defaultStyle);
        layer.redraw();
    }
}
