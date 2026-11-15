"""Rebuild the Hilliard Rome/Renner evidence case from committed snapshots.

python -m pip install -r requirements-demo.txt
python -m scripts.build_local_demo

No network requests or LLM outputs are used to compute findings.
"""
import json
from pathlib import Path
from collections import Counter
from shapely.geometry import shape, Point, mapping
from shapely.ops import transform
from pyproj import Transformer
from rag.tools.local_crashes import crash_counts, load_records, DATA
from rag.config import ROOT

CASE=ROOT/'data/cases/hilliard_rome_renner'
SITE='site_9998d539b0'


def build():
    site=next(s for s in json.loads((DATA/'hotspot_candidates.json').read_text()) if s['hotspot_id']==SITE)
    project=Point(site['longitude'],site['latitude'])
    project_to_m=Transformer.from_crs(4326,26917,always_xy=True).transform
    m_to_geo=Transformer.from_crs(26917,4326,always_xy=True).transform
    centre=transform(project_to_m,project)
    selected_ids=set(site['crash_ids']);crashes=[r for r in load_records() if r['crash_id'] in selected_ids]
    context={};map_features=[]
    kept_fields=['OBJECTID','NLFID','NLF_ID','STATION_ID_NBR','STREET_NAME','LSN','AADT_YEAR','AADT_TOTAL','PERP_YEAR','LANES_NBR','THROUGH_LANES','SPEED_LIMIT_NBR','APPROVED_SPEED','STATUS_OF_REQUEST','WITHDRAWL_REMOVAL_DT','ADACOMPLY','StatusLifeCycle','BEG_POINT_DESCRIPTION_TXT','ENDING_POINT_DESC_TXT']
    for sid in ['odot_traffic_volume','odot_speed_limit','odot_road_inventory','columbus_crosswalks_sidewalks']:
        features=json.loads((CASE/'raw'/f'{sid}.geojson').read_text())['features'];near=[]
        for f in features:
            if not f.get('geometry'):continue
            geom=transform(project_to_m,shape(f['geometry']));distance=geom.distance(centre)
            if distance<=100:
                near.append({'distance_m':round(distance,2),'attributes':{k:v.strip() if isinstance(v,str) else v for k,v in f['properties'].items() if k in kept_fields}})
            if distance<=500:
                map_features.append({'type':'Feature','geometry':f['geometry'],'properties':{'dataset':sid,'OBJECTID':f['properties']['OBJECTID'],'distance_m':round(distance,2)}})
        context[sid]=sorted(near,key=lambda x:x['distance_m'])
    hin=[]
    for f in json.loads((ROOT/'data/local_hin/network.geojson').read_text())['features']:
        dist=transform(project_to_m,shape(f['geometry'])).distance(centre)
        if dist<=100:hin.append({'OBJECTID':f['properties']['OBJECTID'],'street_name':f['properties'].get('STREET_NAM'),'distance_m':round(dist,2)})
        if dist<=500:map_features.append({'type':'Feature','geometry':f['geometry'],'properties':{'dataset':'columbus_hin_webmap_features','OBJECTID':f['properties']['OBJECTID']}})
    for r in crashes:
        map_features.append({'type':'Feature','geometry':mapping(Point(r['longitude'],r['latitude'])),'properties':{'dataset':'odot_crash_snapshot','crash_id':r['crash_id'],'year':r['year'],'severity':r['severity']}})
    map_features.append({'type':'Feature','geometry':mapping(project),'properties':{'dataset':'project_focus','project_id':'119852','hotspot_id':SITE}})
    map_features.append({'type':'Feature','geometry':mapping(transform(m_to_geo,centre.buffer(100))),'properties':{'dataset':'analysis_buffer','radius_m':100}})
    counts=crash_counts(hotspot_id=SITE)
    result={'case_id':'hilliard_rome_renner','project_id':'119852','title':'Hilliard Rome Road at Renner Road: planning evidence demonstration','project_status':'planned improvement per dated project sources; no completed-treatment claim','hotspot_id':SITE,'location':{'longitude':site['longitude'],'latitude':site['latitude'],'analysis_radius_m':100,'distance_crs':'EPSG:26917','output_crs':'EPSG:4326'},'crash_snapshot_date':'2026-09-25','infrastructure_snapshot_date':'2026-11-14','crashes':counts,'radius_sensitivity_crashes':{'75m':site['count_within_75m'],'100m':site['total_crashes'],'150m':site['count_within_150m']},'crash_type_counts':dict(Counter(r['crash_type'] for r in crashes).most_common()),'nearby_infrastructure_100m':context,'hin_features_100m':hin,'interpretation_limits':['Crash records describe 2021–2025 selected-corridor history, not post-project outcomes.','A feature intersecting the 100m buffer is nearby context; not every field applies to every intersection approach.','Do not add adjacent AADT segments or treat a single 2025 AADT as five years of intersection exposure.','Speed-zone approval, roadway inventory and current posted signs are different forms of evidence.','LANES_NBR is not a count of all intersection turning lanes; THROUGH_LANES is null in the selected inventory records.','Crosswalk ADACOMPLY null means unknown, not noncompliant or accessible.','The HIN layer version and crash-attribute periods are not independently established as current.','The COTA Renner Park & Ride facility notice is a separate activity, not proof that PID 119852 construction started.']}
    CASE.mkdir(parents=True,exist_ok=True)
    (CASE/'case.json').write_text(json.dumps(result,indent=2)+'\n')
    (CASE/'map.geojson').write_text(json.dumps({'type':'FeatureCollection','features':map_features})+'\n')
    (CASE/'crashes.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in crashes))
    return result,centre,project_to_m,map_features


def plot(centre,project_to_m,features):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,ax=plt.subplots(figsize=(9,7))
    def line(geom,**kwargs):
        if geom.geom_type=='LineString':ax.plot(*geom.xy,**kwargs)
        elif geom.geom_type=='MultiLineString':
            for g in geom.geoms:line(g,**kwargs)
        elif geom.geom_type=='Polygon':ax.plot(*geom.exterior.xy,**kwargs)
    for f in features:
        name=f['properties']['dataset'];g=transform(project_to_m,shape(f['geometry']))
        if name=='odot_road_inventory':line(g,color='#b8bec7',linewidth=1,zorder=1)
        elif name=='columbus_hin_webmap_features':line(g,color='#e4a338',linewidth=3,alpha=.8,zorder=2)
        elif name=='analysis_buffer':line(g,color='#34495e',linestyle='--',linewidth=1.5,zorder=3)
        elif name=='odot_crash_snapshot':
            serious='serious' in f['properties']['severity'].lower()
            ax.scatter(g.x,g.y,s=35 if serious else 12,color='#bd3d46' if serious else '#226b9c',alpha=.75,zorder=4)
    ax.scatter(centre.x,centre.y,marker='+',s=150,color='black',zorder=5)
    ax.text(centre.x-250,centre.y+38,'Renner Road',fontsize=9,color='#34495e')
    ax.text(centre.x+42,centre.y+130,'Hilliard Rome Road',fontsize=9,rotation=90,color='#34495e')
    ax.set_xlim(centre.x-330,centre.x+330);ax.set_ylim(centre.y-230,centre.y+230);ax.set_aspect('equal')
    ax.set_title('Hilliard Rome / Renner: 131 recorded crashes, 2021–2025\n100 m screening buffer; planned project PID 119852',loc='left',fontweight='bold')
    ax.set_xlabel('Easting, metres (EPSG:26917)');ax.set_ylabel('Northing, metres (EPSG:26917)');ax.ticklabel_format(style='plain',useOffset=False)
    from matplotlib.lines import Line2D
    ax.legend(handles=[Line2D([0],[0],color='#b8bec7',label='Road inventory'),Line2D([0],[0],color='#e4a338',lw=3,label='Catalogued HIN layer'),Line2D([0],[0],marker='o',color='w',markerfacecolor='#226b9c',label='Crash record'),Line2D([0],[0],marker='o',color='w',markerfacecolor='#bd3d46',label='Suspected serious-injury crash')],loc='lower right',fontsize=8)
    fig.text(.09,.02,'ODOT crash snapshot: Sep 25, 2026. Road/HIN snapshots: Nov 14, 2026.\nPoints may overlap. Descriptive screening, not a causal effect estimate or exposure-adjusted ranking.',fontsize=9)
    fig.tight_layout(rect=[0,.07,1,1]);fig.savefig(CASE/'map.png',dpi=170);plt.close(fig)


if __name__=='__main__':
    result,centre,project_to_m,features=build();plot(centre,project_to_m,features)
    print('Built',CASE,'with',result['crashes']['total_crashes'],'crashes')
