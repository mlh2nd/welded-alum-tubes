import streamlit as st
import alumweldzones as alw


st.title("Partially Welded Aluminum Tube Calculator")
st.markdown("This app calculates the section properties of an aluminum tube. \
            Weld-affected zones may be defined to determine strength of partially welded sections, such as guardrails welded to post supports.")
st.markdown("Planned features:")
st.markdown("* Section Property Report\n* ADM ASD and LRFD checks\n* Support for round and arbitrary sections")

st.header("Tube and Weld Properties")
#user_units = st.selectbox("Units", ["kips, inches", "Newtons, millimeters"])
user_units = "kips, inches"
if user_units == "kips, inches":
    force_unit = "kip"
    length_unit = "in"
    stress_unit = "ksi"
    moment_unit = "kip-in"
elif user_units == "Newtons, millimeters":
    force_unit = "N"
    length_unit = "mm"
    stress_unit = "MPa"
mat_grade = st.selectbox("Aluminum Grade", alw.material_list.keys())
tube_type = st.selectbox("Tube Type", ["Rectangular", "Round"])

col1, col2, col3 = st.columns([0.2, 0.3, 0.5])

if tube_type == "Rectangular":
    with col1:
        d = st.number_input(f"Tube Depth ({length_unit})", min_value=0.0, value=2.0)
        b = st.number_input(f"Tube Width ({length_unit})", min_value=0.0, value=3.0)
        t = st.number_input(f"Wall Thickness ({length_unit})", min_value=0.0, value=0.125, step = 0.001)
        r_out = st.number_input(f"Corner Radius ({length_unit})", min_value=0.0, value=0.05, step = 0.001)
    with col2:
        num_zones = st.number_input(f"Number of Weld-Affected Zones", min_value=0, value=1)
        weld_radius = st.number_input(f"Zone Radius ({length_unit}) (Typically 1 inch)", min_value=0.0, value=1.0)
        weld_zones = []
        for zone in range(num_zones):
            side = st.selectbox(f"Weld Zone {zone+1} Side", ["Top", "Bottom", "Left", "Right"])
            position = st.number_input(f"Weld Zone {zone+1} Position ({length_unit})")
            weld_zones.append([side, position])
    visualization, section = alw.define_geom_rect(d, b, t, r_out, weld_zones, weld_radius, mat_grade)
elif tube_type == "Round":
    st.write("This app does not yet support round tubes.")
        
with col3:
    st.pyplot(visualization.plot_geometry().get_figure())
    st.pyplot(section.plot_mesh().get_figure())

section.calculate_geometric_properties()
section.calculate_plastic_properties()
section.calculate_warping_properties()

st.header("Stress Analysis")

col4, col5 = st.columns([0.25, 0.75])

with col4:
    normal_force = st.number_input(f"Normal Force ({force_unit})")
    shear_x = st.number_input(f"Horizontal Shear ({force_unit})")
    shear_y = st.number_input(f"Vertical Shear ({force_unit})")
    moment_x = st.number_input(f"Moment About X-Axis ({moment_unit})")
    moment_y = st.number_input(f"Moment About Y-Axis ({moment_unit})")
    moment_z = st.number_input(f"Torsional Moment ({moment_unit})")

analyzed_section = section.calculate_stress(n=normal_force, vx=shear_x, vy=shear_y, mxx=moment_x, myy=moment_y, mzz=moment_z)

with col5:
    stress_to_plot = st.selectbox("Stress to Plot", ["Von Mises", "σ11", "σ33", "Normal Stress", "Shear Stress"])
    stress = {"Von Mises":"vm", "σ11":"11", "σ33":"33", "Normal Stress":"zz", "Shear Stress":"zxy"}[stress_to_plot]
    st.pyplot(analyzed_section.plot_stress(stress=stress).get_figure())
    col5a, col5b, col5c = st.columns(3)
    with col5a:
        design_method = st.radio("Design Method", ["ASD", "LRFD"])
    with col5b:
        if design_method == "ASD":
            reduction_factor = 1/st.number_input("Safety Factor Ω", value=1.65, min_value = 1.0)
        else: 
            reduction_factor = st.number_input("Strength Factor φ", value=0.90, max_value = 1.0)
    stress_envelope = alw.get_stress_envelope(analyzed_section)
    for weld_condition in stress_envelope:
        stress_envelope[weld_condition][f"Max Stress ({stress_unit})"] = stress_envelope[weld_condition].pop("max")
        stress_envelope[weld_condition][f"Min Stress ({stress_unit})"] = stress_envelope[weld_condition].pop("min")
        if design_method == "ASD":
            stress_envelope[weld_condition][f"Fy/Ω ({stress_unit})"] = stress_envelope[weld_condition].pop("Fy")*reduction_factor
            stress_ratio = stress_envelope[weld_condition][f"Fy/Ω ({stress_unit})"]/max(stress_envelope[weld_condition][f"Max Stress ({stress_unit})"], 
                                                                                        abs(stress_envelope[weld_condition][f"Min Stress ({stress_unit})"]))
        else:
            stress_envelope[weld_condition][f"φFy ({stress_unit})"] = stress_envelope[weld_condition].pop("Fy")*reduction_factor
        stress_envelope[weld_condition].update({"Stress Ratio":stress_ratio})

    st.table(stress_envelope)