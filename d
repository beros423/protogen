[33mcommit f8ed394db11dc373e0b8e8272eb8968b32c6baba[m[33m ([m[1;36mHEAD -> [m[1;32mmain[m[33m, [m[1;31morigin/main[m[33m, [m[1;31morigin/HEAD[m[33m)[m
Author: beros423 <123447806+beros423@users.noreply.github.com>
Date:   Thu Jan 23 18:03:46 2025 +0900

    Update protogen.py

[1mdiff --git a/protogen.py b/protogen.py[m
[1mindex 2d68af9..b353b14 100644[m
[1m--- a/protogen.py[m
[1m+++ b/protogen.py[m
[36m@@ -558,12 +558,11 @@[m [mif uploaded_file is not None:[m
 ################################################################################[m
 [m
 [m
[31m-[m
     # Convert DataFrame to designs format[m
     designs = [][m
     for _, row in design_df.iterrows():[m
         row_volume = sum(vols[col] * row["mk_num"] for col in range(4)) + sum(common['volume'] * row["mk_num"] for common in commons)[m
[31m-        row_repeat = int(row_volume/50)[m
[32m+[m[32m        row_repeat = int((row_volume-0.5)/50) + 1[m[41m[m
         for i in range(row_repeat):[m
             row_design = [][m
             for col, category in enumerate(["Promoter", "CDS", "Terminator", "Connector"]):[m
[36m@@ -627,9 +626,9 @@[m [mif uploaded_file is not None:[m
         with st.expander("Janus protocol"):[m
             protocol, lv1_outputs = generate_janus_protocol(designs, dplate1_name, sources)[m
             st.write("generated mapping:")[m
[31m-            st.write(protocol)[m
[32m+[m[32m            st.write(protocol.reset_index())[m[41m[m
             st.write("generated output plate:")[m
[31m-            st.write(lv1_outputs)[m
[32m+[m[32m            st.write(lv1_outputs.reset_index())[m[41m[m
             st.write("updated sources")[m
             st.write(sources)[m
     for i in range(7):[m
