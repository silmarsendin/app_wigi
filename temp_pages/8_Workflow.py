import streamlit as st
from utils.layout import show_sidebar_branding

st.set_page_config(page_title="Workflow", page_icon="📋", layout="wide")

show_sidebar_branding()

st.title("Project Workflow")
st.write("The images provided in this app are intended solely as visual aids to support learning and memorization. These illustrations were generated using artificial intelligence and may contain minor technical inaccuracies or inconsistencies. Always refer to the applicable codes, standards, manufacturer data sheets, and official technical documentation as the primary and authoritative sources for design, installation, and compliance decisions.")


st.title("Fire Sprinkler Project Workflow")

with st.expander("1. Project Development Process"):
    st.write("Tasks.")

    with st.expander("1.1 Determine Occupancy and Establish Scope of Work:"):
        col1, col2 = st.columns([1, 2])

        with col1:
            st.image("assets/work1_1.png", width=600)

        with col2:
            st.write("If the occupancy is not specified, interview the owner to determine the occupancy of specific use of each space within the building. Establish scope of work for all areas. The owner should provide a signed copy of a completed owner's information certificate.")

    with st.expander("1.2 Develop Design Criteria:"):
        col1, col2 = st.columns([1, 2])

        with col1:
            st.image("assets/work1_2.png", width=600)

        with col2:
            st.write("If the design criteria is specified, verify the criteria is adequate for the occupancy. If the design criteria is not specified, determine the design criteria based cn occupancy and construction. Use Chapter 19 for nonstorage occupancies and Chapters 4. 20. 21. 22. 23, 24. and 25 for storage occupancies. Verify that the design criteria meet local and state codes, along with any NFPA requirements.")

    with st.expander("1.3 Establish Water Supply:"):
        col1, col2 = st.columns([1, 2])

        with col1:
            st.image("assets/work1_3.png", width=600)

        with col2:
            st.write("Crie uma imagem baseada neste texto: If the water supply for the sprinkler system has not been established. evaluate the best option such as as connection, pump and tank, along with other options The water supply must be capable of supplying the water demand of the sprinkler system and hose, for the required duration, in accordance with Chapter 5. Perform a flow test in accordance with NFPA 291.")

    with st.expander("1.4 Coordinate Any Special Equipment:"):
        col1, col2 = st.columns([1, 2])

        with col1:
            st.image("assets/work1_4.png", width=600)

        with col2:
            st.write("If a fire pump, tank and ’or other special equipment is required. coordinate the specifications, electrical, and structural requirements with the appropriate project engineer.")


    with st.expander("1.5 Layout Underground Water Supply:"):
        col1, col2 = st.columns([1, 2])

        with col1:
            st.image("assets/work1_5.png", width=600)

        with col2:
            st.write("The underground fire line supplying the sprinkler system must be drawn in accordance with 27. 1.3 and should include the latest flow test It is important that the fire officials see the locaton of hydrants, pumps, and FDC.")

    with st.expander("1.6 Prepare Preliminary Overhead Layout:"):
        col1, col2 = st.columns([1, 2])

        with col1:
            st.image("assets/work1_6.png", width=600)

        with col2:
            st.write("A preliminary sprinkler head layout must be prepared based on spacing in accordance with Chapters 9 through 16. The sprinkler layout should take into consideration construction and obstruction, including ceiling fixtures. The pipe must be routed in the most hydraulically efficient way along with proper pitching for draining the system.")

    with st.expander("1.7 Prepare Preliminary Hydraulic Calculations:"):
        col1, col2 = st.columns([1, 2])

        with col1:
            st.image("assets/work1_7.png", width=600)

        with col2:
            st.write("A set of hydraulic calculations must be prepared based on the preliminary layout design criteria, and current water supply information in accordance with Chapter 27. Use a flow test that was taken within 12 months of the proposed submittal date in accordance with 4.6.1.1.")

    with st.expander("1.8 Develop a List of Approved and/or Listed Material:"):
        col1, col2 = st.columns([1, 2])

        with col1:
            st.image("assets/work1_8.png", width=600)

        with col2:
            st.write("A detailed list of materials to be used for the project should be developed with attention to approvals, listings, and manufacturer's data sheets. All material must meet the requirements of Chapter 7.")

    with st.expander("1.9 Prepare Eatimate/Pricing:"):
        col1, col2 = st.columns([1, 2])

        with col1:
            st.image("assets/work1_9.png", width=600)

        with col2:
            st.write("A pickofl list of the material showing quantities and pricing should be prepared for the purpose of developing the overall project price. Fabricators and suppliers should be consulted when determining availability and pricing. A list of labor tasks along with related pricing should be prepared and included in the project price.")

    with st.expander("1.10  Prepare Sales Proposal/Contract:"):
        col1, col2 = st.columns([1, 2])

        with col1:
            st.image("assets/work1_10.png", width=600)

        with col2:
            st.write("A sates proposal quotation that includes scope of work, terms. conditions, and price, including any alternatives. should be developed prior to the bid date. Review the buyer's contract for acceptable terms and conditions, including liability, indemnification, and insurance clauses.")

    with st.expander("1.11  Prepare Sales Package:"):
        col1, col2 = st.columns([1, 2])

        with col1:
            st.image("assets/work1_11.png", width=600)

        with col2:
            st.write("A sales package should be developed consisting of a proposal, specifications, CAD drawings, data sheets, pickoff sheets, estimate sheet owner's certificate, preliminary calculations, preliminary layout, and project schedule for the purpose of transferring information to the designer.")

    with st.expander("VISUAL WORKFLOW:"):
        st.markdown("DISCLAMER:")
        st.write("The images provided in this app are intended solely as visual aids to support learning and memorization. These illustrations were generated using artificial intelligence and may contain minor technical inaccuracies or inconsistencies. Always refer to the applicable codes, standards, manufacturer data sheets, and official technical documentation as the primary and authoritative sources for design, installation, and compliance decisions.")
    
        images = [
            "assets/work1_1.png",
            "assets/work1_2.png",
            "assets/work1_3.png",
            "assets/work1_4.png",
            "assets/work1_5.png",
            "assets/work1_6.png",
            "assets/work1_7.png",
            "assets/work1_8.png",
            "assets/work1_9.png",
            "assets/work1_10.png",
            "assets/work1_11.png"
        ]

        captions = [
            "Step 1",
            "Step 2",
            "Step 3",
            "Step 4",
            "Step 5",
            "Step 6",
            "Step 7",
            "Step 8",
            "Step 9",
            "Step 10",
            "Step 11"
        ]

        # Quantidade por linha
        per_row = 4

        for i in range(0, len(images), per_row):
            row_imgs = images[i:i+per_row]
            row_caps = captions[i:i+per_row]

            cols = st.columns(len(row_imgs) * 2 - 1)

            for j, (img, cap) in enumerate(zip(row_imgs, row_caps)):
                cols[j*2].image(img, caption=cap, width=230)

        # seta horizontal entre imagens
                if j < len(row_imgs) - 1:
                    cols[j*2 + 1].markdown(
                        "<div style='font-size:40px; text-align:center; padding-top:60px;'>➡️</div>",
                        unsafe_allow_html=True
                    )

        # seta vertical para próxima linha
            if i + per_row < len(images):
                st.markdown(
                    "<div style='text-align:center; font-size:50px;'>⬇️</div>",
                    unsafe_allow_html=True
                )

with st.expander("2. Design Process"):
    st.write("Tasks")
    
    with st.expander("2.1 Review Project File and Drawings:"):
        col1, col2 = st.columns([1, 2])

        with col1:
            st.image("assets/work2_1.png", width=600)

        with col2:
            st.write("A review of the sales package should be conducted prior to the start of any design. A list of questions should be developed based on the review. A verification that the design criteria meet local and state codes along with any NFPA and owner requirements, should be conducted before proceeding with the design of the piping layout.")

    
    with st.expander("2.2  Conduct Pre-design Meeting:"):
        col1, col2 = st.columns([1, 2])

        with col1:
            st.image("assets/work2_2.png", width=600)

        with col2:
            st.write("A pre-design of hand-off meeting between sales and design should be conducted prior to the start of design. The purpose of the meeting is to ensure that all parties have a clear understanding of the overall project, including the scope of work, approval process, schedule, and any special owner requirements.")
 
    with st.expander("2.3  Review Schedule and Establish Milestones:"):
        col1, col2 = st.columns([1, 2])

        with col1:
            st.image("assets/work2_3.png", width=600)

        with col2:
            st.write("Based on a complete review of the project schedule, establish milestones such as dates for submitting drawings, approvals. permitting, field checking, ordering material, fabrication, material delivery installation, testing, and completing as-built drawings. Factor into the schedule my special order items that may have long lead-times.")


    with st.expander("2.4  Clean Up CAD Files:"):
        col1, col2 = st.columns([1, 2])

        with col1:
            st.image("assets/work2_4.png", width=600)

        with col2:
            st.write("The project CAD files from the architect need to be cleaned up by deleting or turning off unnecessary layers and Information that do not relate to the fire protection drawings. At a minimum, the drawings must include what Is listed in 27.1.9.")

    with st.expander("2.5  Layout Underground, Pump and/or Tank:"):
        col1, col2 = st.columns([1, 2])

        with col1:
            st.image("assets/work2_5.png", width=600)

        with col2:
            st.write("Use the civil drawings that show the city main to layout the underground supply to the fire protection system(s). If the water supply consists of a fire pimp and/or tank, depict it on the civil drawing, If possible. This will keep all the water supply and related equipment on the same drawing. The FDC and hydrants should located on this drawing as well to assist the authority having jurisdiction in reviewing and planning.")

    with st.expander("2.6  Space and Layout Fre Sprinklers:"):
        col1, col2 = st.columns([1, 2])

        with col1:
            st.image("assets/work2_6.png", width=600)

        with col2:
            st.write("All fire sprinklers must be spaced in accordance with Chapters 9 through 15 based on the type of construction, occupancy, fire sprinkler type, and obstruction concerns.")

    with st.expander("2.7  Route Piping:"):
        col1, col2 = st.columns([1, 2])

        with col1:
            st.image("assets/work2_7.png", width=600)

        with col2:
            st.write("All sprinkler pipe must be routed in the hydraulically most efficient way, taking into consideration the ease of installation, along with obstructions, clearance heights, other building trades, and features.")

    with st.expander("2.8  Coordinate Piping With Other Trades:"):
        col1, col2 = st.columns([1, 2])

        with col1:
            st.image("assets/work2_8.png", width=600)

        with col2:
            st.write("Always consider other trades when routing pipe. Contact other trades when routing pipe in a congested area to coordinate the exact location and height to avoid conflicts during Installation. Follow RFI process to resolve any unclear issues. B.I.M. (Building Information Modeling) may be required for virtual coordination on some projects.")

    with st.expander("2.9  Perform Hydraulic Calculations:"):
        col1, col2 = st.columns([1, 2])

        with col1:
            st.image("assets/work2_9.png", width=600)

        with col2:
            st.write("Always select the hydraulically most remote area In accordance with Chapter 27. It may be necessary to calculate several areas to verify the hydraulically most remote area. If the property has a mixed occupancy each occupancy may need to be calculated depending on location end hazard.")

    with st.expander("2.10  Design Hangers and Bracing:"):
        col1, col2 = st.columns([1, 2])

        with col1:
            st.image("assets/work2_10.png", width=600)

        with col2:
            st.write("All hangers need to be spaced and designed in accordance with Chapters 17 and 18 based on the type of construction and pipe size. if the system must be protected against damage from earthquakes, follow the requirements of Chapter 18.")

    with st.expander("2.11  Note Details:"):
        col1, col2 = st.columns([1, 2])

        with col1:
            st.image("assets/work2_11.png", width=600)

        with col2:
            st.write("Clearly note the scope of work, the design criteria for the system, and any special conditions. Any special conditions, hose stations, fire pumps, riser diagrams, and hangers should be detailed to give the Installer a better understanding of the equipment and arrangement.")

    with st.expander("2.12   Review Plans Prior to Submittal:"):
        col1, col2 = st.columns([1, 2])

        with col1:
            st.image("assets/work2_12.png", width=600)

        with col2:
            st.write("Review plans and calculations for completeness using NFPA 13 - Chapter 27. Review plans and calculations to make sure they are in accordance with the contract documents, local codes and applicable NFPA documents.")

    with st.expander("2.13  Submit Plans to Authority Having Jurisdiction in Accordance With Local Requirements:"):
        col1, col2 = st.columns([1, 2])

        with col1:
            st.image("assets/work2_13.png", width=600)

        with col2:
            st.write("Submit plans, calculations and product data sheets to the local authority having jurisdiction for a permit in accordance with local requirements. Always consider the review turn round time when scheduling the project.")

    with st.expander("2.14  Track Approvals:"):
        col1, col2 = st.columns([1, 2])

        with col1:
            st.image("assets/work2_14.png", width=600)

        with col2:
            st.write("Always track the approval process and make follow-up cells to avoid delays to the project schedule.")

    with st.expander("2.15  Field Check Project:"):
        col1, col2 = st.columns([1, 2])

        with col1:
            st.image("assets/work2_15.png", width=600)

        with col2:
            st.write("All projects should be field checked prior to stocklisting them, to verify the structure is constructe in strict accordance with the building plans.")

    with st.expander("2.16  Prepare Drawing for Stocklisting and Fabrication:"):
        col1, col2 = st.columns([1, 2])

        with col1:
            st.image("assets/work2_16.png", width=600)

        with col2:
            st.write("Based on the results of the field check, adjust the drawing accordingly. Verify all mains and line notations are shown along with any special equipment.")

    with st.expander("VISUAL WORKFLOW:"):
        st.markdown("DISCLAMER:")
        st.write("The images provided in this app are intended solely as visual aids to support learning and memorization. These illustrations were generated using artificial intelligence and may contain minor technical inaccuracies or inconsistencies. Always refer to the applicable codes, standards, manufacturer data sheets, and official technical documentation as the primary and authoritative sources for design, installation, and compliance decisions.")
    
        images = [
            "assets/work2_1.png",
            "assets/work2_2.png",
            "assets/work2_3.png",
            "assets/work2_4.png",
            "assets/work2_5.png",
            "assets/work2_6.png",
            "assets/work2_7.png",
            "assets/work2_8.png",
            "assets/work2_9.png",
            "assets/work2_10.png",
            "assets/work2_11.png",
            "assets/work2_12.png",
            "assets/work2_13.png",
            "assets/work2_14.png",
            "assets/work2_15.png",
            "assets/work2_16.png"
        ]

        captions = [
            "Step 1",
            "Step 2",
            "Step 3",
            "Step 4",
            "Step 5",
            "Step 6",
            "Step 7",
            "Step 8",
            "Step 9",
            "Step 10",
            "Step 11",
            "Step 12",
            "Step 13",
            "Step 14",
            "Step 15",
            "Step 16",
        ]

        # Quantidade por linha
        per_row = 4

        for i in range(0, len(images), per_row):
            row_imgs = images[i:i+per_row]
            row_caps = captions[i:i+per_row]

            cols = st.columns(len(row_imgs) * 2 - 1)

            for j, (img, cap) in enumerate(zip(row_imgs, row_caps)):
                cols[j*2].image(img, caption=cap, width=230)

        # seta horizontal entre imagens
                if j < len(row_imgs) - 1:
                    cols[j*2 + 1].markdown(
                        "<div style='font-size:40px; text-align:center; padding-top:60px;'>➡️</div>",
                        unsafe_allow_html=True
                    )

        # seta vertical para próxima linha
            if i + per_row < len(images):
                st.markdown(
                    "<div style='text-align:center; font-size:50px;'>⬇️</div>",
                    unsafe_allow_html=True
                )

with st.expander("3. Fabrication Process"):
    st.write("Tasks")
 
    with st.expander("3.1 Stocklist the Material:"):
        col1, col2 = st.columns([1, 2])

        with col1:
            st.image("assets/work3_1.png", width=600)

        with col2:
            st.write("Stocklist the material in accordance with the material specifications and the approved material data sheets for the project. Verify all material components are in accordance with NFPA - Chapter 7.")

    with st.expander("3.2 Purchase the Material:"):
        col1, col2 = st.columns([1, 2])

        with col1:
            st.image("assets/work3_2.png", width=600)

        with col2:
            st.write("Based on competitive pricing, purchase the material based on the specifications and the approved material data sheets for the project.")

    with st.expander("3.3 Fabricate the Material:"):
        col1, col2 = st.columns([1, 2])

        with col1:
            st.image("assets/work3_3.png", width=600)

        with col2:
            st.write("All fabrication must be in accordance with NFPA 13 Chapter 7, with special attention to the requirements of welded fabrication in 7.5.2.")
    
    with st.expander("VISUAL WORKFLOW:"):
        st.markdown("DISCLAMER:")
        st.write("The images provided in this app are intended solely as visual aids to support learning and memorization. These illustrations were generated using artificial intelligence and may contain minor technical inaccuracies or inconsistencies. Always refer to the applicable codes, standards, manufacturer data sheets, and official technical documentation as the primary and authoritative sources for design, installation, and compliance decisions.")
    
        images = [
            "assets/work3_1.png",
            "assets/work3_2.png",
            "assets/work3_3.png"
        ]

        captions = [
            "Step 1",
            "Step 2",
            "Step 3"
        ]

        # Quantidade por linha
        per_row = 4

        for i in range(0, len(images), per_row):
            row_imgs = images[i:i+per_row]
            row_caps = captions[i:i+per_row]

            cols = st.columns(len(row_imgs) * 2 - 1)

            for j, (img, cap) in enumerate(zip(row_imgs, row_caps)):
                cols[j*2].image(img, caption=cap, width=230)

        # seta horizontal entre imagens
                if j < len(row_imgs) - 1:
                    cols[j*2 + 1].markdown(
                        "<div style='font-size:40px; text-align:center; padding-top:60px;'>➡️</div>",
                        unsafe_allow_html=True
                    )

        # seta vertical para próxima linha
            if i + per_row < len(images):
                st.markdown(
                    "<div style='text-align:center; font-size:50px;'>⬇️</div>",
                    unsafe_allow_html=True
                )

with st.expander("4. Installation Process"):
    st.write("Tasks")

    with st.expander("4.1  Conduct Pre-construction Meeting:"):
        col1, col2 = st.columns([1, 2])

        with col1:
            st.image("assets/work4_1.png", width=600)

        with col2:
            st.write("A pre-construction meeting should be held with the installation foreman, superintendent, and the designer prior to the start of the installation. The purpose of this meeting is to go over the drawings in detail, the contract documents, job schedule and the results of the coordination with other trades.")

    with st.expander("4.2  Establish Materials Staging Area;"):
        col1, col2 = st.columns([1, 2])

        with col1:
            st.image("assets/work4_2.png", width=600)

        with col2:
            st.write("A staging area for all materials should be established with the contractor’s superintendent prior to the delivery of materials. Organize and field-verify material counts. The staging area should be close to the installation area yet out of the way of other trades.")

    with st.expander("4.3  Review Safety Tools and Equipament:"):
        col1, col2 = st.columns([1, 2])

        with col1:
            st.image("assets/work4_3.png", width=600)

        with col2:
            st.write("It is important that installers are equipped with the proper tools and equipment to aid in the installation of the project in the most efficient way. They must be properly trained on how to use the equipment in a safe manner.")

    with st.expander("4.4  Review Safety Equipament:"):
        col1, col2 = st.columns([1, 2])

        with col1:
            st.image("assets/work4_4.png", width=600)

        with col2:
            st.write("Review and inspect all safety equipment, along with training records, to ensure a safe installation process.")

    with st.expander("4.5  Start at Riser:"):
        col1, col2 = st.columns([1, 2])

        with col1:
            st.image("assets/work4_5.png", width=600)

        with col2:
            st.write("It is always a good idea to start the installation from the riser to avoid having to adjust the main piping later.")

    with st.expander("4.6  Rough-in Work:"):
        col1, col2 = st.columns([1, 2])

        with col1:
            st.image("assets/work4_6.png", width=600)

        with col2:
            st.write("Install the system in accordance with the installations drawings, verifying the fire sprinkler are in compliance with the spacing and obstruction rules in NFP 13 Chapters 9 through 16. Once the system is completely roughed-in, prepare a punchlist of any remaining to-do items.")

    with st.expander("4.7  Perform Testing Prior to Approvals:"):
        col1, col2 = st.columns([1, 2])

        with col1:
            st.image("assets/work4_7.png", width=600)

        with col2:
            st.write("Always perform the proper test on the system in accordance with Chapter 28 from NFPA 13 prior to the authority having jurisdiction required acceptance test If the results are acceptable, then contact the authority having jurisdiction to set up the finaI acceptance test.")

    with st.expander("4.8  Finish Work:"):
        col1, col2 = st.columns([1, 2])

        with col1:
            st.image("assets/work4_8.png", width=600)

        with col2:
            st.write("Once the ceilings and walls are finished, install the required fire sprinkler escutcheons, wall plates, head cabinets and hose equipment. Installing them last will keep them free from dirt and debris. Complete any punch list items.")

    with st.expander("4.9  Prepare As-built Drawings:"):
        col1, col2 = st.columns([1, 2])

        with col1:
            st.image("assets/work4_9.png", width=600)

        with col2:
            st.write("Prepare a set of as-built drawing based co feedback from the installation crew on any adjustments they may have made to the original installation drawings.")

    with st.expander("4.10  Submit Closeout Documents"):
        col1, col2 = st.columns([1, 2])

        with col1:
            st.image("assets/work4_10.png", width=600)

        with col2:
            st.write("Submit closeout documents in accordance with the contract documents that include as-built drawings, material data sheets, warranties, and a copy of the applicable sections of NFPA 25.")

    with st.expander("4.11  Present Owner Training:"):
        col1, col2 = st.columns([1, 2])

        with col1:
            st.image("assets/work4_11.png", width=600)

        with col2:
            st.write("Present a training session on all the new fire protection equipment to the owner's representative. Document who received the training and when it was held.")

    with st.expander("VISUAL WORKFLOW:"):
        st.markdown("DISCLAMER:")
        st.write("The images provided in this app are intended solely as visual aids to support learning and memorization. These illustrations were generated using artificial intelligence and may contain minor technical inaccuracies or inconsistencies. Always refer to the applicable codes, standards, manufacturer data sheets, and official technical documentation as the primary and authoritative sources for design, installation, and compliance decisions.")
    
        images = [
            "assets/work4_1.png",
            "assets/work4_2.png",
            "assets/work4_3.png",
            "assets/work4_4.png",
            "assets/work4_5.png",
            "assets/work4_6.png",
            "assets/work4_7.png",
            "assets/work4_8.png",
            "assets/work4_9.png",
            "assets/work4_10.png",
            "assets/work4_11.png"
        ]

        captions = [
            "Step 1",
            "Step 2",
            "Step 3",
            "Step 4",
            "Step 5",
            "Step 6",
            "Step 7",
            "Step 8",
            "Step 9",
            "Step 10",
            "Step 11",

        ]

        # Quantidade por linha
        per_row = 4

        for i in range(0, len(images), per_row):
            row_imgs = images[i:i+per_row]
            row_caps = captions[i:i+per_row]

            cols = st.columns(len(row_imgs) * 2 - 1)

            for j, (img, cap) in enumerate(zip(row_imgs, row_caps)):
                cols[j*2].image(img, caption=cap, width=230)

        # seta horizontal entre imagens
                if j < len(row_imgs) - 1:
                    cols[j*2 + 1].markdown(
                        "<div style='font-size:40px; text-align:center; padding-top:60px;'>➡️</div>",
                        unsafe_allow_html=True
                    )

        # seta vertical para próxima linha
            if i + per_row < len(images):
                st.markdown(
                    "<div style='text-align:center; font-size:50px;'>⬇️</div>",
                    unsafe_allow_html=True
                )


st.image("assets/workflow.png", use_container_width=True)  