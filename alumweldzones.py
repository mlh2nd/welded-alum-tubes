import sectionproperties.pre.library as prelib
from sectionproperties.pre.pre import Material
from sectionproperties.analysis.section import Section

material_list = {
                    "6061-T6": {
                        "Fty":35.0, 
                        "Ftyw":15.0, 
                        "E":10100, 
                        "nu":0.33, 
                        "rho":0.1},
                    "5052-H32": {
                        "Fty":23.0, 
                        "Ftyw":9.5, 
                        "E":10100, 
                        "nu":0.33, 
                        "rho":0.1}
                }


unwelded_color = "silver"
welded_color = "firebrick"


def define_materials(grade:str) -> tuple[Material, Material]:
    """
    Returns unwelded and welded material objects for sectionproperties processing
    """
    mat_props = material_list[grade]
    unwelded = Material(
                        name=f"{grade} - Unwelded",
                        elastic_modulus = mat_props["E"],
                        poissons_ratio = mat_props["nu"],
                        yield_strength = mat_props["Fty"],
                        density = mat_props["rho"],
                        color = unwelded_color
                     )
    welded = Material(
                        name=f"{grade} - Welded",
                        elastic_modulus = mat_props["E"],
                        poissons_ratio = mat_props["nu"],
                        yield_strength = mat_props["Ftyw"],
                        density = mat_props["rho"],
                        color = welded_color
                     )
    return unwelded, welded


def define_geom_rect(d, b, t, r_out, weld_zones, weld_radius, grade):
    """
    Defines geometry for partially welded rectangular section
    d, b, t, r_out, and grade are section dimensions.
    weld_zones is a list containing the face and position of each welded zone.
    """
    unwelded, welded = define_materials(grade)
    tube_geom = prelib.rectangular_hollow_section(d, b, t, r_out, 12, unwelded)
    weld_geom = []
    for zone in weld_zones:
        face = zone[0].lower()
        position = zone[1]
        if face == "left":
            x_offset = weld_radius
            y_offset = position
        elif face == "right":
            x_offset = -weld_radius
            y_offset = position
        elif face == "top":
            x_offset = position
            y_offset = -weld_radius
        elif face == "bottom":
            x_offset = position
            y_offset = weld_radius
        weld_geom.append(prelib.primitive_sections.circular_section(weld_radius*2, 24, welded)
                         .align_to(tube_geom, on=face).shift_section(x_offset, y_offset))
    
    combined_for_visualization = tube_geom
    combined_for_analysis = tube_geom
    for weld in weld_geom:
        combined_for_visualization += weld
        unwelded_region = combined_for_analysis - weld
        welded_region = weld & combined_for_analysis
        combined_for_analysis = unwelded_region + welded_region

    combined_for_analysis.create_mesh(t/5)
    section = Section(combined_for_analysis, time_info=True)
    
    return combined_for_visualization, section


def get_stress_envelope(analyzed_section, design_method, factor):
    results = analyzed_section.get_stress()
    results_dict = {}
    if design_method == "ASD":
        reduction_factor = 1/factor
    elif design_method == "LRFD":
        reduction_factor = factor
    for mat in results:
        mat_name = mat["material"]
        mat_short_name = mat_name.replace(" - Welded", "").replace(" - Unwelded", "")
        if "Unwelded" in mat_name:
            Fy = material_list[mat_short_name]["Fty"]
        else:
            Fy = material_list[mat_short_name]["Ftyw"]
        max_stress, min_stress = 0.0, 0.0
        for stress_array in mat.values():
            if isinstance(stress_array, str):
                continue
            if stress_array.max() > max_stress:
                max_stress = stress_array.max()
            if stress_array.min() < min_stress:
                min_stress = stress_array.min()
        stress_ratio = max(max_stress, abs(min_stress)) / (Fy*reduction_factor)
        results_dict.update({mat_name:{"max":max_stress, "min":min_stress, "Fy":Fy, "SR":stress_ratio}})
    return results_dict