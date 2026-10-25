# Compact sla thor reference study

Primary visual reference: Pich Sovann PS, **របៀបធ្វើស្លាធម៌សំរាប់រៀបដាក់កន្លែងគ្រូបាធ្យាយ / How to make Slarture Baysei/baysey mongkol**, published July 4, 2020.

- https://www.youtube.com/watch?v=UyxSQ51YRMg
- Inspected the actual video at **00:04, 10:46, 12:50–12:51 and 13:23**, not only its thumbnail.
- The maker prepares short, pale cut banana-stem sections, exposes their moist, layered cut surfaces, presses small dark areca pieces into them, and pins individually handled/folded betel leaves into the stems. Loose folded leaves, bamboo pins and unassembled stems are visible beside the maker.
- The final examples have a few broad, sharply folded leaves with open spaces between them. They do not have concentric downward-pointing skirts, five diminishing radial tiers or a flower finial.

The model follows that compact construction: three separate broad betel leaves with rolled lower sides and pinched folds on a short, slightly uneven stem, with exposed end grain, tiny bamboo pins and three split areca pieces. Each leaf has branching veins, irregular margins, a separate underside and a pointed tip. Height and placement are adapted to the existing game shelf; this is a modeled interpretation of this maker's example, not a claim of a universal ritual form or verified historical reconstruction of a 1932 household altar. No reference photograph or video frame is copied into game textures.

Context consulted:

- Trần Minh Thương's survey distinguishes **Sla Thor Thommada**, **Sla Thor Sot Mon**, coconut variants and tiered **Baysei Ruot**. It concerns Khmer communities in southern Vietnam and is used to avoid conflating the forms, not as the Cambodian visual reference: https://phatgiaobaclieu.com/dkhao-sat-cac-vat-dung-trong-nghi-thuc-cung-te-ths-tran-minh-thuong/
- Than Sok's *Objects of Belief — Sla Thor Kon Chek* is described by the artist's gallery as banana leaves, betel leaves and betel nuts in a banana-stalk base. The gallery PDF was access-blocked during visual retrieval, so its artwork was **not** used as the silhouette reference: https://rkfineart.com/wp-content/uploads/2019/07/RKFA_Catalogue_Currents_Than-Sok-2019.07.24-Interactives.pdf

Rejected visual results: a Cambodian seller's mislabeled umbrella photograph, food photographs, a forest-offering variant, and inaccessible social-media images. None was treated as evidence for the modeled leaf arrangement.

Rebuild only this object with `tools/areas/rebuild-slathor.py`. The full house builder imports the same geometry through `hall_altar.py`. The targeted exporter verifies shelf contact, compact proportions, three separate leaves, upward-facing cut-surface polygons and unchanged transforms/data for all other scene objects; the GLB merge checks that only `hall_slathor` is replaced.
