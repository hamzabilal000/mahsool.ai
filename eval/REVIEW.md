# Eval review — test split

140 unverified questions. For each one, tick the boxes that are true and note anything wrong. Then tell Claude Code which ids to fix; verified ones get `"verified": true` in `eval/testset.jsonl`.

What to check:
- **Gold is right:** the gold section really answers the question (open the PDF page if unsure).
- **Reference answer is right** according to that section.
- **Translation is natural:** the Urdu / Roman Urdu reads like something a person would actually type, and means the same as the English.

Regenerate this file with `python -m eval.make_review`.

## In-scope questions

### en-001 · lookup · easy

> What does section 4 of the Income Tax Ordinance impose tax on, and at which rates?

- **ITO2001-s4** ([PDF p. 52](https://download1.fbr.gov.pk/Docs/2026724177725705IncomeTaxOrdinanace2001.pdf#page=52)): 4. Tax on taxable income.— (1) Subject to this Ordinance, income tax shall be imposed for each tax year, at the rate or rates specified in [Division I or II] of Part I of the First Schedule, as the case may be, on every person who has taxable income for the year. (2) The income tax payable by a taxp …

Reference answer: Income tax is imposed for each tax year on every person who has taxable income for the year, at the rates in Division I or II of Part I of the First Schedule; tax credits are then subtracted from the resulting amount.

- [ ] en-001: gold section answers the question
- [ ] en-001: reference answer is correct

### en-002 · rate · easy

> At what rate is the surcharge under section 4AB charged, and above what level of taxable income?

- **ITO2001-s4AB** ([PDF p. 53](https://download1.fbr.gov.pk/Docs/2026724177725705IncomeTaxOrdinanace2001.pdf#page=53)): [[4AB] Subject to this Ordinance, a surcharge shall be payable by every individual and association of persons at the rate of ten percent of the income tax imposed under Division I of Part I of the First Schedule where the taxable income exceeds rupees ten million [: Provided that in case of an indiv …

Reference answer: Individuals and associations of persons pay a surcharge of ten percent of the income tax under Division I of Part I of the First Schedule where taxable income exceeds Rs. 10 million.

- [ ] en-002: gold section answers the question
- [ ] en-002: reference answer is correct
- [ ] ur-013 (Urdu) reads naturally and means the same: دفعہ 4AB کے تحت سرچارج کی شرح کیا ہے اور یہ کتنی قابل ٹیکس آمدن سے زیادہ پر لگتا ہے؟
- [ ] ru-013 (Roman Urdu) reads naturally and means the same: 4AB surcharge ka rate kya hai aur kitni income pe lagta hai?

### en-005 · multi_section · medium

> What is the super tax rate for a banking company whose income exceeds Rs. 150 million?

- **ITO2001-s4C** ([PDF p. 54](https://download1.fbr.gov.pk/Docs/2026724177725705IncomeTaxOrdinanace2001.pdf#page=54)): [4C. Super tax on high earning persons.― (1) A super tax shall be imposed for tax year 2022 and onwards at the rates specified in Division IIB of Part I of the First Schedule, on income of every person: Provided that this section shall not apply to a banking company for tax year 2022. (2) For the pu …
- **ITO2001-sch1-pI-divIIB** ([PDF p. 531](https://download1.fbr.gov.pk/Docs/2026724177725705IncomeTaxOrdinanace2001.pdf#page=531)): First Schedule, Part I, Division IIB [Division IIB Super Tax on high earning persons The rate of tax under section 4C shall be – [TABLE | S. No. | Income under section 4C and person | Rate of Tax | |---|---|---| | 1. | Income of a banking company exceeding Rs. 150 million | 10% of the income | | 2. …

Reference answer: 10% of the income (Division IIB, Part I, First Schedule, serial 1), levied under section 4C.

- [ ] en-005: gold section answers the question
- [ ] en-005: reference answer is correct

### en-006 · rate · medium

> What super tax rate applies to a person other than a bank, a fertilizer seller or a Fifth Schedule person whose income exceeds Rs. 500 million?

- **ITO2001-sch1-pI-divIIB** ([PDF p. 531](https://download1.fbr.gov.pk/Docs/2026724177725705IncomeTaxOrdinanace2001.pdf#page=531)): First Schedule, Part I, Division IIB [Division IIB Super Tax on high earning persons The rate of tax under section 4C shall be – [TABLE | S. No. | Income under section 4C and person | Rate of Tax | |---|---|---| | 1. | Income of a banking company exceeding Rs. 150 million | 10% of the income | | 2. …

Reference answer: 8% of the income (Division IIB, Part I, First Schedule, serial 4).

- [ ] en-006: gold section answers the question
- [ ] en-006: reference answer is correct

### en-008 · conditions · medium

> Does the separate tax on profit on debt under section 7B apply if my profit on debt exceeds Rs. 5 million?

- **ITO2001-s7B** ([PDF p. 60](https://download1.fbr.gov.pk/Docs/2026724177725705IncomeTaxOrdinanace2001.pdf#page=60)): [7B. Tax on profit on debt.—(1) Subject to this Ordinance, a tax shall be imposed, at the rate specified in Division IIIA of Part I of the First Schedule, on every person, other than a company, who receives a profit on debt from any person mentioned in clauses (a) to (d) of sub-section (1)of section …

Reference answer: No. Section 7B does not apply to profit on debt that is exempt or that exceeds five million rupees.

- [ ] en-008: gold section answers the question
- [ ] en-008: reference answer is correct

### en-010 · lookup · easy

> What are the heads of income under the Income Tax Ordinance?

- **ITO2001-s11** ([PDF p. 66](https://download1.fbr.gov.pk/Docs/2026724177725705IncomeTaxOrdinanace2001.pdf#page=66)): 11. Heads of income.— (1) For the purposes of the imposition of tax and the computation of total income, all income shall be classified under the following heads, namely: — (a) Salary; [(b) Income from Property;] [(c) Income from Business;] [(d) Capital Gains; and] [(e) Income from Other Sources.] ( …

Reference answer: Salary; Income from Property; Income from Business; Capital Gains; and Income from Other Sources.

- [ ] en-010: gold section answers the question
- [ ] en-010: reference answer is correct

### en-011 · lookup · easy

> Are overtime payments and bonuses part of salary for income tax purposes?

- **ITO2001-s12** ([PDF p. 68](https://download1.fbr.gov.pk/Docs/2026724177725705IncomeTaxOrdinanace2001.pdf#page=68)): 12. Salary.— (1) Any salary received by an employee in a tax year, other than salary that is exempt from tax under this Ordinance, shall be chargeable to tax in that year under the head “Salary”. (2) Salary means any amount received by an employee from any employment, whether of a revenue or capital …

Reference answer: Yes. Salary includes pay, wages and other remuneration such as leave pay, overtime, bonus, commission, fees, gratuity and work-condition supplements.

- [ ] en-011: gold section answers the question
- [ ] en-011: reference answer is correct
- [ ] ur-014 (Urdu) reads naturally and means the same: کیا اوور ٹائم اور بونس انکم ٹیکس کے لیے تنخواہ کا حصہ سمجھے جاتے ہیں؟
- [ ] ru-014 (Roman Urdu) reads naturally and means the same: overtime aur bonus bhi salary me shamil hote hain tax k liye?

### en-013 · multi_section · medium

> How is a car provided by an employer for an employee's private use taxed?

- **ITO2001-s13** ([PDF p. 70](https://download1.fbr.gov.pk/Docs/2026724177725705IncomeTaxOrdinanace2001.pdf#page=70)): 13. Value of perquisites.— (1) For the purposes of computing the income of an employee for a tax year chargeable to tax under the head “Salary”, the value of any perquisite provided by an employer to the employee in that year that is included in the employee’s salary under section 12 shall be determ …
- **ITR2002-r5** ([PDF p. 18](https://download1.fbr.gov.pk/Docs/20269211394336470IncomeTaxRules2002.pdf#page=18)): 5. Valuation of conveyance.- The value of conveyance provided by the employer to the employee shall be taken equal to an amount as below:- (i) Partly for 5% of: personal and (a) the cost to the employer for acquiring the partly for official motor vehicle; or, use (b) the fair market value of the mot …

Reference answer: Section 13(3) adds a prescribed amount to salary; under rule 5 it is 5% (partly personal, partly official use) or 10% (personal use only) of the employer's cost of the vehicle, or of its fair market value at the start of the lease if leased.

- [ ] en-013: gold section answers the question
- [ ] en-013: reference answer is correct
- [ ] ur-015 (Urdu) reads naturally and means the same: کمپنی کی طرف سے ذاتی استعمال کے لیے دی گئی گاڑی پر ملازم کو ٹیکس کیسے لگتا ہے؟
- [ ] ru-015 (Roman Urdu) reads naturally and means the same: office ki gaari ghar ke kaam k liye bhi use karta hun, is pe tax kaise lagta hai?

### en-014 · lookup · easy

> What counts as 'rent' under section 15 of the Income Tax Ordinance?

- **ITO2001-s15** ([PDF p. 76](https://download1.fbr.gov.pk/Docs/2026724177725705IncomeTaxOrdinanace2001.pdf#page=76)): 15. Income from property.— (1) The rent received or receivable by a person [for] a tax year, other than rent exempt from tax under this Ordinance, shall be chargeable to tax in that year under the head “Income from Property”. (2) Subject to sub-section (3), “rent” means any amount received or receiv …

Reference answer: Any amount received or receivable by the owner of land or a building for the use or occupation (or right to use or occupy) of it, including a forfeited deposit under a contract for sale of land or a building.

- [ ] en-014: gold section answers the question
- [ ] en-014: reference answer is correct

### en-015 · lookup · easy

> Is agricultural income taxable under the federal Income Tax Ordinance?

- **ITO2001-s41** ([PDF p. 119](https://download1.fbr.gov.pk/Docs/2026724177725705IncomeTaxOrdinanace2001.pdf#page=119)): 41. Agricultural income. — (1) Agricultural income derived by a person shall be exempt from tax under this Ordinance. (2) In this section, “agricultural income” means, — (a) any rent or revenue derived by a person from land which is situated in Pakistan and is used for agricultural purposes; (b) any …

Reference answer: No. Agricultural income, such as rent or revenue from land in Pakistan used for agricultural purposes, is exempt under section 41.

- [ ] en-015: gold section answers the question
- [ ] en-015: reference answer is correct
- [ ] ur-016 (Urdu) reads naturally and means the same: کیا وفاقی انکم ٹیکس قانون کے تحت زرعی آمدن پر ٹیکس لگتا ہے؟
- [ ] ru-016 (Roman Urdu) reads naturally and means the same: zameen ki fasal se jo income hoti hai us pe federal income tax hai kya?

### en-016 · conditions · easy

> Is a scholarship received to pay for my education taxable?

- **ITO2001-s47** ([PDF p. 123](https://download1.fbr.gov.pk/Docs/2026724177725705IncomeTaxOrdinanace2001.pdf#page=123)): 47. Scholarships.— Any scholarship granted to a person to meet the cost of the person’s education shall be exempt from tax under this Ordinance, other than where the scholarship is paid directly or indirectly by an associate.

Reference answer: No, a scholarship granted to meet the cost of education is exempt, unless it is paid directly or indirectly by an associate.

- [ ] en-016: gold section answers the question
- [ ] en-016: reference answer is correct
- [ ] ur-017 (Urdu) reads naturally and means the same: تعلیم کے لیے ملنے والے وظیفے (اسکالرشپ) پر ٹیکس لگتا ہے؟
- [ ] ru-017 (Roman Urdu) reads naturally and means the same: parhai ke liye scholarship milti hai, us pe tax lagega?

### en-017 · lookup · easy

> Is support money received by a spouse under an agreement to live apart taxable?

- **ITO2001-s48** ([PDF p. 123](https://download1.fbr.gov.pk/Docs/2026724177725705IncomeTaxOrdinanace2001.pdf#page=123)): 48. Support payments under an agreement to live apart.—[Any income received by a spouse as support payment under an agreement to live apart] shall be exempt from tax under this Ordinance.

Reference answer: No. Income received by a spouse as support payment under an agreement to live apart is exempt.

- [ ] en-017: gold section answers the question
- [ ] en-017: reference answer is correct

### en-019 · conditions · medium

> When is the foreign-source income of a short-term resident individual exempt?

- **ITO2001-s50** ([PDF p. 124](https://download1.fbr.gov.pk/Docs/2026724177725705IncomeTaxOrdinanace2001.pdf#page=124)): 50. Foreign-source income of short-term resident individuals.— (1) Subject to sub-section (2), the foreign-source income of an individual — (a) who is a resident individual solely by reason of the individual’s employment; and (b) who is present in Pakistan for a period or periods not exceeding three …

Reference answer: When the individual is resident solely because of employment and is present in Pakistan for no more than three years; it does not apply to income from a business established in Pakistan or to foreign-source income brought into or received in Pakistan.

- [ ] en-019: gold section answers the question
- [ ] en-019: reference answer is correct

### en-020 · lookup · easy

> For how many years can an unabsorbed business loss be carried forward?

- **ITO2001-s57** ([PDF p. 128](https://download1.fbr.gov.pk/Docs/2026724177725705IncomeTaxOrdinanace2001.pdf#page=128)): 57. Carry forward of business losses.—(1) Where a person sustains a loss for a tax year under the head “Income from Business” (other than a loss to which [sub-section (4) or] section 58 applies) and the loss cannot be wholly set off under section 56, so much of the loss that has not been set off sha …

Reference answer: A business loss not set off can be carried forward against business income, but not to more than six tax years immediately succeeding the year in which the loss was first computed.

- [ ] en-020: gold section answers the question
- [ ] en-020: reference answer is correct
- [ ] ur-018 (Urdu) reads naturally and means the same: کاروباری نقصان کو کتنے سال تک آگے لے جایا جا سکتا ہے؟
- [ ] ru-018 (Roman Urdu) reads naturally and means the same: business ka loss kitne saal tak carry forward ho sakta hai?

### en-022 · conditions · easy

> Can I claim Zakat paid as a deduction, and can unused Zakat be carried forward?

- **ITO2001-s60** ([PDF p. 137](https://download1.fbr.gov.pk/Docs/2026724177725705IncomeTaxOrdinanace2001.pdf#page=137)): 60. Zakat.— (1) A person shall be entitled to a deductible allowance for the amount of any Zakat paid by the person in a tax year under the Zakat and Ushr Ordinance, 1980 (XVIII of 1980). (2) Sub-section (1) does not apply to any Zakat taken into account under sub-section (2) of section 40. (3) Any …

Reference answer: Zakat paid under the Zakat and Ushr Ordinance, 1980 is a deductible allowance; any part that cannot be deducted in the year is not refunded or carried forward or back.

- [ ] en-022: gold section answers the question
- [ ] en-022: reference answer is correct
- [ ] ur-019 (Urdu) reads naturally and means the same: کیا ادا کی گئی زکوٰۃ پر ٹیکس میں کٹوتی ملتی ہے، اور بچ جانے والی رقم اگلے سال لے جا سکتے ہیں؟
- [ ] ru-019 (Roman Urdu) reads naturally and means the same: zakat di hai to tax me kami hogi? jo bach jaye wo agle saal le ja sakte hain?

### en-023 · conditions · medium

> Who can claim the deductible allowance for children's tuition fee, and how much?

- **ITO2001-s60D** ([PDF p. 138](https://download1.fbr.gov.pk/Docs/2026724177725705IncomeTaxOrdinanace2001.pdf#page=138)): [60D. Deductible allowance for education expenses.— (1) Every individual shall be entitled to a deductible allowance in respect of tuition fee paid by the individual in a tax year provided that the taxable income of the individual is less than one [and a half]million rupees. (2) The amount of an ind …

Reference answer: An individual with taxable income below Rs. 1.5 million; the allowance is the lesser of 5% of tuition fee paid, 25% of taxable income, and Rs. 60,000 multiplied by the number of children.

- [ ] en-023: gold section answers the question
- [ ] en-023: reference answer is correct
- [ ] ur-020 (Urdu) reads naturally and means the same: بچوں کی ٹیوشن فیس پر ٹیکس میں کٹوتی کون لے سکتا ہے اور کتنی؟
- [ ] ru-020 (Roman Urdu) reads naturally and means the same: bachon ki school fees pe tax me koi chhoot milti hai? kitni?

### en-024 · conditions · easy

> Is Workers' Welfare Fund paid by a business deductible?

- **ITO2001-s60A** ([PDF p. 137](https://download1.fbr.gov.pk/Docs/2026724177725705IncomeTaxOrdinanace2001.pdf#page=137)): [60A. Workers’ Welfare Fund.— A person shall be entitled to a deductible allowance for the amount of any Workers’ Welfare Fund paid by the person in tax year under Workers’ Welfare Fund Ordinance, 1971 (XXXVI of 1971) [or under any law relating to the Workers’ Welfare Fund enacted by Provinces after …

Reference answer: Yes. Workers' Welfare Fund paid under the 1971 Ordinance or a provincial WWF law is a deductible allowance (not for amounts paid to Provinces by a trans-provincial establishment).

- [ ] en-024: gold section answers the question
- [ ] en-024: reference answer is correct

### en-025 · lookup · easy

> Do I get a tax benefit for donating to a public university?

- **ITO2001-s61** ([PDF p. 139](https://download1.fbr.gov.pk/Docs/2026724177725705IncomeTaxOrdinanace2001.pdf#page=139)): 61. Charitable donations.—[(1) A person shall be entitled to a tax credit in respect of any sum paid, or any property given by the person in the tax year as a donation [, voluntary contribution or subscription] to — (a) any board of education or any university in Pakistan established by, or under, a …

Reference answer: Yes. Donations to a board of education or a university established under Federal or Provincial law qualify for a tax credit under section 61, computed by formula.

- [ ] en-025: gold section answers the question
- [ ] en-025: reference answer is correct
- [ ] ur-021 (Urdu) reads naturally and means the same: کیا سرکاری یونیورسٹی کو عطیہ دینے پر ٹیکس میں کوئی فائدہ ملتا ہے؟
- [ ] ru-021 (Roman Urdu) reads naturally and means the same: sarkari university ko donation diya, tax me koi faida milega?

### en-026 · conditions · medium

> Who is entitled to a tax credit for contributions to an approved pension fund?

- **ITO2001-s63** ([PDF p. 142](https://download1.fbr.gov.pk/Docs/2026724177725705IncomeTaxOrdinanace2001.pdf#page=142)): [63. Contribution to an Approved Pension Fund.— (1) An eligible person as defined in sub-section (19A) of section 2 deriving income chargeable to tax under the head “Salary” or the head “Income from Business” shall be entitled to a tax credit for a tax year in respect of any contribution or premium …

Reference answer: An eligible person (section 2(19A)) with salary or business income who contributes to an approved pension fund under the Voluntary Pension System Rules, 2005.

- [ ] en-026: gold section answers the question
- [ ] en-026: reference answer is correct

### en-027 · conditions · medium

> Is there a tax credit for profit paid on a housing loan?

- **ITO2001-s63A** ([PDF p. 144](https://download1.fbr.gov.pk/Docs/2026724177725705IncomeTaxOrdinanace2001.pdf#page=144)): [63A. Tax credit for interest paid on low-cost housing loan. — (1) An individual shall be entitled to a tax credit for a tax year in respect of any profit on debt or share in rent or share in appreciation for value of house paid by the person in the year on a loan by a scheduled bank or any other fi …

Reference answer: Yes. An individual gets a tax credit for profit on debt paid on a loan from a scheduled bank or other specified lender used to construct or acquire one personal house within the section's limits.

- [ ] en-027: gold section answers the question
- [ ] en-027: reference answer is correct

### en-028 · lookup · easy

> What is the 'tax year' under the Income Tax Ordinance?

- **ITO2001-s74** ([PDF p. 160](https://download1.fbr.gov.pk/Docs/2026724177725705IncomeTaxOrdinanace2001.pdf#page=160)): [74. Tax year.— (1) For the purpose of this Ordinance and subject to this section, the tax year shall be a period of twelve months ending on the 30th day of June (hereinafter referred to as ‘normal tax year’) and shall, subject to sub-section (3), be denoted by the calendar year in which the said da …

Reference answer: A twelve-month period ending on 30 June (the normal tax year), named after the calendar year in which that date falls.

- [ ] en-028: gold section answers the question
- [ ] en-028: reference answer is correct

### en-029 · lookup · easy

> How many days must an individual be present in Pakistan to be a resident individual?

- **ITO2001-s82** ([PDF p. 170](https://download1.fbr.gov.pk/Docs/2026724177725705IncomeTaxOrdinanace2001.pdf#page=170)): 82. Resident individual. — An individual shall be a resident individual for a tax year if the individual — (a) is present in Pakistan for a period of, or periods amounting in aggregate to, one hundred and [eighty-three] days or more in the tax year; [or] (c) is an employee or official of the Federal …

Reference answer: 183 days or more in the tax year (in one or more periods).

- [ ] en-029: gold section answers the question
- [ ] en-029: reference answer is correct
- [ ] ur-022 (Urdu) reads naturally and means the same: ریذیڈنٹ شمار ہونے کے لیے ایک ٹیکس سال میں کتنے دن پاکستان میں رہنا ضروری ہے؟
- [ ] ru-022 (Roman Urdu) reads naturally and means the same: resident banne k liye pakistan me kitne din rehna zaroori hai?

### en-030 · conditions · hard

> Can a Pakistani citizen who spends much of the year abroad still be a resident individual?

- **ITO2001-s82** ([PDF p. 170](https://download1.fbr.gov.pk/Docs/2026724177725705IncomeTaxOrdinanace2001.pdf#page=170)): 82. Resident individual. — An individual shall be a resident individual for a tax year if the individual — (a) is present in Pakistan for a period of, or periods amounting in aggregate to, one hundred and [eighty-three] days or more in the tax year; [or] (c) is an employee or official of the Federal …

Reference answer: Yes, if the citizen is not present in any other country for more than 182 days in the tax year, or is not a resident taxpayer of any other country.

- [ ] en-030: gold section answers the question
- [ ] en-030: reference answer is correct
- [ ] ur-023 (Urdu) reads naturally and means the same: کیا سال کا زیادہ حصہ بیرون ملک گزارنے والا پاکستانی شہری پھر بھی ریذیڈنٹ شمار ہو سکتا ہے؟
- [ ] ru-023 (Roman Urdu) reads naturally and means the same: saal ka zyada time bahar rehta hun, phir bhi resident count hounga kya?

### en-031 · lookup · easy

> When is a company treated as a resident company?

- **ITO2001-s83** ([PDF p. 171](https://download1.fbr.gov.pk/Docs/2026724177725705IncomeTaxOrdinanace2001.pdf#page=171)): 83. Resident company.— A company shall be a resident company for a tax year if — (a) it is incorporated or formed by or under any law in force in Pakistan; (b) the control and management of the affairs of the company is situated wholly in Pakistan at any time in the year; or (c) it is a Provincial G …

Reference answer: If it is incorporated under Pakistani law, its control and management is wholly in Pakistan at any time in the year, or it is a Provincial Government or Local Government.

- [ ] en-031: gold section answers the question
- [ ] en-031: reference answer is correct

### en-032 · conditions · medium

> Is foreign salary received by a resident individual taxed in Pakistan if tax was already paid abroad?

- **ITO2001-s102** ([PDF p. 215](https://download1.fbr.gov.pk/Docs/2026724177725705IncomeTaxOrdinanace2001.pdf#page=215)): 102. Foreign source salary of resident individuals.— (1) Any foreign-source salary received by a resident individual shall be exempt from tax if the individual has paid foreign income tax in respect of the salary. (2) A resident individual shall be treated as having paid foreign income tax in respec …

Reference answer: It is exempt if foreign income tax was paid on it, e.g. withheld by the employer and paid to the foreign country's revenue authority.

- [ ] en-032: gold section answers the question
- [ ] en-032: reference answer is correct
- [ ] ur-024 (Urdu) reads naturally and means the same: اگر بیرون ملک کی تنخواہ پر وہاں ٹیکس کٹ چکا ہو تو کیا پاکستان میں بھی اس پر ٹیکس لگے گا؟
- [ ] ru-024 (Roman Urdu) reads naturally and means the same: dubai ki salary pe wahan tax kat gaya, pakistan me bhi dena parega?

### en-033 · lookup · medium

> How much foreign tax credit is allowed on foreign-source income?

- **ITO2001-s103** ([PDF p. 215](https://download1.fbr.gov.pk/Docs/2026724177725705IncomeTaxOrdinanace2001.pdf#page=215)): 103. Foreign tax credit.— (1) Where a resident taxpayer derives foreign source income chargeable to tax under this Ordinance in respect of which the taxpayer has paid foreign income tax, the taxpayer shall be allowed a tax credit of an amount equal to the lesser of – (a) the foreign income tax paid; …

Reference answer: The lesser of the foreign income tax paid and the Pakistan tax payable on that income.

- [ ] en-033: gold section answers the question
- [ ] en-033: reference answer is correct

### en-034 · lookup · medium

> When is salary Pakistan-source income?

- **ITO2001-s101** ([PDF p. 208](https://download1.fbr.gov.pk/Docs/2026724177725705IncomeTaxOrdinanace2001.pdf#page=208)): 101. Geographical source of income. — (1) Salary shall be Pakistan-source income to the extent to which the salary — (a) is received from any employment exercised in Pakistan, wherever paid; or (b) is paid by, or on behalf of, the Federal Government, a Provincial Government, or a [Local Government] …

Reference answer: When it is from employment exercised in Pakistan (wherever paid), or when it is paid by the Federal, a Provincial or a Local Government wherever the employment is exercised.

- [ ] en-034: gold section answers the question
- [ ] en-034: reference answer is correct

### en-035 · conditions · medium

> What happens if I cannot explain the source of an investment or money I own?

- **ITO2001-s111** ([PDF p. 230](https://download1.fbr.gov.pk/Docs/2026724177725705IncomeTaxOrdinanace2001.pdf#page=230)): 111. Unexplained income or assets. — (1) Where — (a) any amount is credited in a person’s books of account; (b) a person has made any investment or is the owner of any money or valuable article; (c) a person has incurred any expenditure[; or] [(d) any person has concealed income or furnished inaccur …

Reference answer: If no explanation is offered, or the Commissioner finds it unsatisfactory, the unexplained amount is included in the person's income chargeable to tax.

- [ ] en-035: gold section answers the question
- [ ] en-035: reference answer is correct

### en-036 · conditions · medium

> Which persons are covered by minimum tax under section 113?

- **ITO2001-s113** ([PDF p. 234](https://download1.fbr.gov.pk/Docs/2026724177725705IncomeTaxOrdinanace2001.pdf#page=234)): [113. Minimum tax on the income of certain persons.- (1) This section shall apply to a resident company,[permanent establishment of a non-resident company,] [, an individual (having turnover of [hundred] million rupees or above in the tax year [2017] or in any subsequent tax year) and an association …

Reference answer: Resident companies, permanent establishments of non-resident companies, and individuals and AOPs with turnover of Rs. 100 million or more in tax year 2017 or later.

- [ ] en-036: gold section answers the question
- [ ] en-036: reference answer is correct

### en-037 · lookup · medium

> Who is required to file an income tax return?

- **ITO2001-s114** ([PDF p. 241](https://download1.fbr.gov.pk/Docs/2026724177725705IncomeTaxOrdinanace2001.pdf#page=241)): 114. Return of income. — (1) Subject to this Ordinance, the following persons are required to furnish a return of income for a tax year, namely:– [(a) every company;] [(ab) every person (other than a company) whose taxable income for the year exceeds the maximum amount that is not chargeable to tax …

Reference answer: Among others: every company; every other person whose taxable income exceeds the non-taxable limit; non-profit organizations; persons whose income is subject to final taxation; and persons meeting the conditions in section 114(1)(b).

- [ ] en-037: gold section answers the question
- [ ] en-037: reference answer is correct
- [ ] ur-025 (Urdu) reads naturally and means the same: انکم ٹیکس ریٹرن جمع کرانا کس کس کے لیے لازمی ہے؟
- [ ] ru-025 (Roman Urdu) reads naturally and means the same: income tax return kis kis ko file karni zaroori hai?

### en-039 · multi_section · hard

> Does a widow who owns a 500 square yard house have to file a return only because of that property?

- **ITO2001-s115** ([PDF p. 252](https://download1.fbr.gov.pk/Docs/2026724177725705IncomeTaxOrdinanace2001.pdf#page=252)): 115. Persons not required to furnish a return of income. — (3) The following persons shall not be required to furnish a return of income for a tax year solely by reason of [sub-clause (iii)[, (iv),(v) and (vi)]] of clause (b) of sub-section (1) of section 114 – (a) A widow; (b) an orphan below the a …
- **ITO2001-s114** ([PDF p. 241](https://download1.fbr.gov.pk/Docs/2026724177725705IncomeTaxOrdinanace2001.pdf#page=241)): 114. Return of income. — (1) Subject to this Ordinance, the following persons are required to furnish a return of income for a tax year, namely:– [(a) every company;] [(ab) every person (other than a company) whose taxable income for the year exceeds the maximum amount that is not chargeable to tax …

Reference answer: No. Section 115(3) exempts a widow, an orphan under 25, a disabled person, and (for property) a non-resident from filing solely because of those property clauses of section 114.

- [ ] en-039: gold section answers the question
- [ ] en-039: reference answer is correct
- [ ] ur-026 (Urdu) reads naturally and means the same: کیا 500 مربع گز کے گھر کی مالک بیوہ کو صرف اس جائیداد کی وجہ سے ریٹرن جمع کرانا ہوگا؟
- [ ] ru-026 (Roman Urdu) reads naturally and means the same: widow hain aur 500 gaz ka ghar hai, sirf is wajah se return deni paregi?

### en-041 · lookup · easy

> What can the Commissioner ask for in a wealth statement?

- **ITO2001-s116** ([PDF p. 253](https://download1.fbr.gov.pk/Docs/2026724177725705IncomeTaxOrdinanace2001.pdf#page=253)): 116. Wealth statement.— (1) [The] Commissioner may, by notice in writing, require any person [being an individual] to furnish, on the date specified in the notice, a statement (hereinafter referred to as the "wealth statement") in the prescribed form and verified in the prescribed manner giving part …

Reference answer: By notice, an individual's total assets and liabilities (including foreign ones) and those of the spouse, minor children and other dependents, as of the dates specified.

- [ ] en-041: gold section answers the question
- [ ] en-041: reference answer is correct

### en-042 · lookup · easy

> What is the due date for a salaried individual to file the income tax return?

- **ITO2001-s118** ([PDF p. 256](https://download1.fbr.gov.pk/Docs/2026724177725705IncomeTaxOrdinanace2001.pdf#page=256)): 118. Method of furnishing returns and other documents. — (1) A return of income under section 114, [,] a wealth statement under section 116 [or a foreign income and assets statement under 116A, if applicable] shall be furnished in the prescribed manner. (2) A return of income [under section 114 ] of …

Reference answer: On or before 30 September following the end of the tax year.

- [ ] en-042: gold section answers the question
- [ ] en-042: reference answer is correct
- [ ] ur-027 (Urdu) reads naturally and means the same: تنخواہ دار فرد کے لیے انکم ٹیکس ریٹرن جمع کرانے کی آخری تاریخ کیا ہے؟
- [ ] ru-027 (Roman Urdu) reads naturally and means the same: salaried bande ki return ki last date kya hai?

### en-045 · lookup · easy

> How can I get more time to file my income tax return?

- **ITO2001-s119** ([PDF p. 258](https://download1.fbr.gov.pk/Docs/2026724177725705IncomeTaxOrdinanace2001.pdf#page=258)): 119. Extension of time for furnishing returns and other documents.— (1) A person required to furnish — (a) a return of income under section 114 or 117; (d) a wealth statement under section 116, may apply, in writing, to the Commissioner for an extension of time to furnish the return, or statement, a …

Reference answer: Apply in writing to the Commissioner for an extension, by the due date for filing the return.

- [ ] en-045: gold section answers the question
- [ ] en-045: reference answer is correct
- [ ] ur-028 (Urdu) reads naturally and means the same: انکم ٹیکس ریٹرن جمع کرانے کے لیے مزید وقت کیسے لیا جا سکتا ہے؟
- [ ] ru-028 (Roman Urdu) reads naturally and means the same: return file karne ke liye extra time kaise milta hai?

### en-047 · lookup · medium

> How long does the Commissioner have to amend an assessment?

- **ITO2001-s122** ([PDF p. 266](https://download1.fbr.gov.pk/Docs/2026724177725705IncomeTaxOrdinanace2001.pdf#page=266)): 122. Amendment of assessments.— (1) Subject to this section, the Commissioner may amend an assessment order treated as issued under section 120 or issued under section 121[, [or , by making such alterations or additions as the Commissioner considers necessary . [(2) No order under sub-section (1) sh …

Reference answer: No amendment after five years from the end of the financial year in which the assessment order was issued or treated as issued.

- [ ] en-047: gold section answers the question
- [ ] en-047: reference answer is correct

### en-048 · lookup · easy

> What is the deadline to appeal to the Appellate Tribunal against an order of the Commissioner (Appeals)?

- **ITO2001-s131** ([PDF p. 287](https://download1.fbr.gov.pk/Docs/2026724177725705IncomeTaxOrdinanace2001.pdf#page=287)): [131. Appeal to the Appellate Tribunal. — [(1) Where the taxpayer, or the Commissioner objects to an order passed by the Commissioner (Appeals), the taxpayer or Commissioner may appeal to the Appellate Tribunal against such order within thirty days of the receipt of such order: Provided that the tax …

Reference answer: Within thirty days of receiving the order.

- [ ] en-048: gold section answers the question
- [ ] en-048: reference answer is correct

### en-050 · lookup · easy

> When is income tax on my taxable income due for payment?

- **ITO2001-s137** ([PDF p. 308](https://download1.fbr.gov.pk/Docs/2026724177725705IncomeTaxOrdinanace2001.pdf#page=308)): 137. Due date for payment of tax.— (1) The tax payable by a taxpayer on the taxable income of the taxpayer [including the tax payable under ] [section [113 or] 113A] for a tax year shall be due on the due date for furnishing the taxpayer’s return of income for that year. [(2) Where any tax is payabl …

Reference answer: On the due date for furnishing the return of income for that year.

- [ ] en-050: gold section answers the question
- [ ] en-050: reference answer is correct
- [ ] ur-029 (Urdu) reads naturally and means the same: قابل ٹیکس آمدن پر ٹیکس کب تک ادا کرنا ہوتا ہے؟
- [ ] ru-029 (Roman Urdu) reads naturally and means the same: income pe jo tax banta hai wo kab tak jama karwana hota hai?

### en-052 · conditions · hard

> Is income subject to salary withholding under section 149 included when computing quarterly advance tax under section 147?

- **ITO2001-s147** ([PDF p. 321](https://download1.fbr.gov.pk/Docs/2026724177725705IncomeTaxOrdinanace2001.pdf#page=321)): 147. Advance tax paid by the taxpayer.— (1) Subject to sub-section (2), every taxpayer [whose income was charged to tax for the latest tax year under this Ordinance or latest assessment year under the repealed Ordinance] other than – (b) income chargeable to tax under sections 5, 6 and 7; (c) income …

Reference answer: No. Income subject to deduction at source under section 149 is excluded from the income on which section 147 advance tax is computed.

- [ ] en-052: gold section answers the question
- [ ] en-052: reference answer is correct

### en-054 · conditions · hard

> Is tax deducted from pension paid to a retired employee?

- **ITO2001-s149** ([PDF p. 333](https://download1.fbr.gov.pk/Docs/2026724177725705IncomeTaxOrdinanace2001.pdf#page=333)): 149. Salary. — (1) Every [person responsible for] paying salary to an employee shall, at the time of payment, deduct tax from the amount paid at the employee’s average rate of tax computed at the rates specified in Division I of Part I of the First Schedule on the estimated income of the employee ch …

Reference answer: Under section 149(1A), where pension to a former employee below 70 exceeds Rs. 10 million in a tax year, tax is deducted on the amount above Rs. 10 million at Division I rates, along with section 4AB tax.

- [ ] en-054: gold section answers the question
- [ ] en-054: reference answer is correct
- [ ] ur-030 (Urdu) reads naturally and means the same: کیا ریٹائرڈ ملازم کی پنشن پر ٹیکس کٹتا ہے؟
- [ ] ru-030 (Roman Urdu) reads naturally and means the same: retire ho gaya hun, pension pe tax katega kya?

### en-057 · lookup · easy

> Who must deduct withholding tax on profit on debt under section 151?

- **ITO2001-s151** ([PDF p. 335](https://download1.fbr.gov.pk/Docs/2026724177725705IncomeTaxOrdinanace2001.pdf#page=335)): 151. Profit on debt. — (1) Where – [(a) a person pays yield on an account, deposit or a certificate under the National Savings Scheme or Post Office Savings Account;] (b) a banking company [or] financial institution pays any profit on a debt, being an account or deposit maintained with the company o …

Reference answer: Payers of yield on National Savings or Post Office accounts; banking companies and financial institutions on accounts or deposits; governments paying profit on securities; and other specified payers.

- [ ] en-057: gold section answers the question
- [ ] en-057: reference answer is correct

### en-058 · lookup · easy

> How is tax withheld on royalty or fees for technical services paid to a non-resident?

- **ITO2001-s152** ([PDF p. 337](https://download1.fbr.gov.pk/Docs/2026724177725705IncomeTaxOrdinanace2001.pdf#page=337)): 152. Payments to non-residents.— (1) Every person paying an amount of [royalty] or fees for technical services to a non-resident person that is chargeable to tax under section 6 shall deduct tax from the gross amount paid at the rate specified in Division IV of Part I of the First Schedule. [(1A) Ev …

Reference answer: The payer deducts tax from the gross amount at the rate in Division IV of Part I of the First Schedule.

- [ ] en-058: gold section answers the question
- [ ] en-058: reference answer is correct

### en-060 · conditions · medium

> Below what yearly total do payments for services escape withholding under section 153?

- **ITO2001-s153** ([PDF p. 346](https://download1.fbr.gov.pk/Docs/2026724177725705IncomeTaxOrdinanace2001.pdf#page=346)): [153. Payments for goods, services and contracts.— (1) Every prescribed person making a payment in full or part including a payment by way of advance to a resident person — (a) for the sale of goods [including toll manufacturing] [, except where payment is less than seventy-five thousand Rupees in a …

Reference answer: Payments for services below Rs. 30,000 in aggregate during a financial year.

- [ ] en-060: gold section answers the question
- [ ] en-060: reference answer is correct

### en-061 · multi_section · medium

> How much tax is deducted on export proceeds of IT services for an exporter registered with PSEB?

- **ITO2001-s154A** ([PDF p. 356](https://download1.fbr.gov.pk/Docs/2026724177725705IncomeTaxOrdinanace2001.pdf#page=356)): [154A. Export of Services. — (1) Every authorized dealer in foreign exchange shall, at the time of realization of foreign exchange proceeds on account of the following, deduct tax from the proceeds at the rates specified in Division IVA of Part III of the First Schedule – (a) exports of computer sof …
- **ITO2001-sch1-pIII-divIVA** ([PDF p. 566](https://download1.fbr.gov.pk/Docs/2026724177725705IncomeTaxOrdinanace2001.pdf#page=566)): First Schedule, Part III, Division IVA [DIVISION IVA Export of Services The rate of tax to be deducted under section 154A shall be:- | S. No. | Types of Receipts | Rate of Tax | |---|---|---| | (1) | (2) | (3) | | 1. | Export proceeds of Computer software or IT services or IT Enabled services by per …
- also acceptable: WHT2027-s154A

Reference answer: The authorized dealer deducts 0.25% of the proceeds (for tax years 2024 to 2029) when the exporter is registered with the Pakistan Software Export Board.

- [ ] en-061: gold section answers the question
- [ ] en-061: reference answer is correct
- [ ] ur-031 (Urdu) reads naturally and means the same: پی ایس ای بی میں رجسٹرڈ فری لانسر کی بیرون ملک سے آنے والی آئی ٹی آمدن پر کتنا ٹیکس کٹتا ہے؟
- [ ] ru-031 (Roman Urdu) reads naturally and means the same: freelancer hun PSEB registered, bahar se paisa aye to kitna tax kat ta hai?

### en-062 · rate · medium

> What rate is deducted on export of services proceeds if the exporter is not registered with PSEB?

- **ITO2001-sch1-pIII-divIVA** ([PDF p. 566](https://download1.fbr.gov.pk/Docs/2026724177725705IncomeTaxOrdinanace2001.pdf#page=566)): First Schedule, Part III, Division IVA [DIVISION IVA Export of Services The rate of tax to be deducted under section 154A shall be:- | S. No. | Types of Receipts | Rate of Tax | |---|---|---| | (1) | (2) | (3) | | 1. | Export proceeds of Computer software or IT services or IT Enabled services by per …
- also acceptable: WHT2027-s154A

Reference answer: 1% of the proceeds ('any other case', Division IVA, Part III, First Schedule).

- [ ] en-062: gold section answers the question
- [ ] en-062: reference answer is correct

### en-063 · numeric · hard

> An individual landlord receives Rs. 500,000 rent a year. How much tax should the tenant withhold under section 155?

- **ITO2001-s155** ([PDF p. 358](https://download1.fbr.gov.pk/Docs/2026724177725705IncomeTaxOrdinanace2001.pdf#page=358)): 155. [Rent of immoveable] property.— (1) [Every] prescribed person making a payment in full or part (including a payment by way of advance) to any person on account of rent of immovable property (including rent of furniture and fixtures, and amounts for services relating to such property) shall dedu …
- **ITO2001-sch1-pIII-divV** ([PDF p. 567](https://download1.fbr.gov.pk/Docs/2026724177725705IncomeTaxOrdinanace2001.pdf#page=567)): First Schedule, Part III, Division V [Division V Income from Property (a) The rate of tax to be deducted under section 155, in the case of individual and association of persons, shall be— [TABLE | S. No. | Gross amount of rent | Rate of tax | |---|---|---| | (1) | (2) | (3) | | 1. | Where the gross …
- also acceptable: WHT2027-s155

Reference answer: 5% of the amount exceeding Rs. 300,000: 5% x 200,000 = Rs. 10,000 (Division V, Part III, First Schedule, slab Rs. 300,001 to 600,000).

- [ ] en-063: gold section answers the question
- [ ] en-063: reference answer is correct
- [ ] ur-032 (Urdu) reads naturally and means the same: ایک مالک مکان کو سال میں پانچ لاکھ روپے کرایہ ملتا ہے۔ کرایہ دار کو کتنا ٹیکس کاٹنا چاہیے؟
- [ ] ru-032 (Roman Urdu) reads naturally and means the same: makan ka kiraya 5 lakh saalana hai, kirayedar kitna tax kaate ga?

### en-065 · multi_section · medium

> How much tax is deducted on prize bond winnings, and is it final?

- **ITO2001-s156** ([PDF p. 359](https://download1.fbr.gov.pk/Docs/2026724177725705IncomeTaxOrdinanace2001.pdf#page=359)): 156. Prizes and winnings.—(1) Every person paying [prize on] a prize bond, or winnings from a raffle, lottery, [prize on winning a quiz, prize offered by companies for promotion of sale,] or cross-word puzzle shall deduct tax from the gross amount paid at the rate specified in Division VI of Part II …
- **ITO2001-sch1-pIII-divVI** ([PDF p. 569](https://download1.fbr.gov.pk/Docs/2026724177725705IncomeTaxOrdinanace2001.pdf#page=569)): First Schedule, Part III, Division VI Division VI Prizes and Winnings (1) The rate of tax to be deducted under section 156 on a prize on prize bond or cross-word puzzle shall be [15]% of the gross amount paid (2) The rate of tax to be deducted under section 156 on winnings from a raffle, lottery, pr …
- also acceptable: WHT2027-s156

Reference answer: 15% of the gross amount paid (Division VI, Part III), and under section 156(3) the tax is a final tax.

- [ ] en-065: gold section answers the question
- [ ] en-065: reference answer is correct
- [ ] ur-033 (Urdu) reads naturally and means the same: پرائز بانڈ کے انعام پر کتنا ٹیکس کٹتا ہے اور کیا یہ حتمی ٹیکس ہے؟
- [ ] ru-033 (Roman Urdu) reads naturally and means the same: prize bond ka inaam nikla hai, kitna tax katega aur kya ye final hai?

### en-066 · rate · easy

> What is the tax rate on lottery, raffle or quiz winnings?

- **ITO2001-sch1-pIII-divVI** ([PDF p. 569](https://download1.fbr.gov.pk/Docs/2026724177725705IncomeTaxOrdinanace2001.pdf#page=569)): First Schedule, Part III, Division VI Division VI Prizes and Winnings (1) The rate of tax to be deducted under section 156 on a prize on prize bond or cross-word puzzle shall be [15]% of the gross amount paid (2) The rate of tax to be deducted under section 156 on winnings from a raffle, lottery, pr …
- also acceptable: WHT2027-s156

Reference answer: 20% of the gross amount paid.

- [ ] en-066: gold section answers the question
- [ ] en-066: reference answer is correct

### en-067 · lookup · medium

> How can I stop tax being withheld from payments that are exempt or taxed at a lower rate?

- **ITO2001-s159** ([PDF p. 362](https://download1.fbr.gov.pk/Docs/2026724177725705IncomeTaxOrdinanace2001.pdf#page=362)): 159. Exemption or lower rate certificate.— (1) Where the Commissioner is satisfied that an amount to which Division II or III of this Part [or Chapter XII] applies is – (a) exempt from tax under this Ordinance; or (b) subject to tax at a rate lower than that specified in the First Schedule [; or (c) …

Reference answer: Apply in writing (in the prescribed form) to the Commissioner for an exemption or lower rate certificate.

- [ ] en-067: gold section answers the question
- [ ] en-067: reference answer is correct

### en-068 · conditions · medium

> What happens if a withholding agent fails to deduct tax?

- **ITO2001-s161** ([PDF p. 364](https://download1.fbr.gov.pk/Docs/2026724177725705IncomeTaxOrdinanace2001.pdf#page=364)): 161. Failure to pay tax collected or deducted.— (1) Where a person– (a) fails to collect tax as required under Division II of this Part [or Chapter XII] or deduct tax from a payment as required under Division III of this Part [or Chapter XII] [or as required under section 50 of the repealed Ordinanc …

Reference answer: The person becomes personally liable to pay the tax to the Commissioner, who may pass an order and recover it after giving an opportunity of being heard.

- [ ] en-068: gold section answers the question
- [ ] en-068: reference answer is correct

### en-070 · lookup · medium

> Can I adjust tax deducted at source against my final tax liability?

- **ITO2001-s168** ([PDF p. 376](https://download1.fbr.gov.pk/Docs/2026724177725705IncomeTaxOrdinanace2001.pdf#page=376)): 168. Credit for tax collected or deducted. — (1) For the purposes of this Ordinance — (a) the amount of any tax deducted from a payment under Division III of this Part [or Chapter XII] shall be treated as income derived by the person to whom the payment was made; and (b) the amount of any tax collec …

Reference answer: Yes, subject to exceptions: tax collected or deducted is treated as tax paid, and a tax credit is allowed for the tax year in which it was collected or deducted.

- [ ] en-070: gold section answers the question
- [ ] en-070: reference answer is correct
- [ ] ur-034 (Urdu) reads naturally and means the same: کیا منبع پر کٹا ہوا ٹیکس میری کل ٹیکس ذمہ داری میں ایڈجسٹ ہو سکتا ہے؟
- [ ] ru-034 (Roman Urdu) reads naturally and means the same: jo tax source pe kat gaya wo meri total tax liability me adjust hoga?

### en-071 · lookup · medium

> What does it mean when tax deducted is a 'final tax' under section 169?

- **ITO2001-s169** ([PDF p. 378](https://download1.fbr.gov.pk/Docs/2026724177725705IncomeTaxOrdinanace2001.pdf#page=378)): 169. Tax collected or deducted as a final tax.— (1) This section shall apply where — (b) the [tax required to be deducted] is a final tax under [sub-section (1E) of section 152, 152A], [sub-section (2) of section 154A] [, clause (b) of sub-section (3) of section 154B,] sub-section (3) of section 156 …

Reference answer: The income is not chargeable under any head in computing taxable income, and no deduction is allowed for expenditure incurred in deriving it.

- [ ] en-071: gold section answers the question
- [ ] en-071: reference answer is correct

### en-072 · lookup · medium

> How long does the Commissioner have to decide my refund application?

- **ITO2001-s170** ([PDF p. 382](https://download1.fbr.gov.pk/Docs/2026724177725705IncomeTaxOrdinanace2001.pdf#page=382)): 170. Refunds.— (1) A taxpayer who has paid tax in excess of the amount which the taxpayer is properly chargeable under this Ordinance may apply to the Commissioner for a refund of the excess. [(1A) Where any advance or loan, to which sub-clause (e) of clause (19) of section 2 applies, is repaid by a …

Reference answer: Within sixty days of receiving the application, the Commissioner must serve a written order after giving an opportunity of being heard.

- [ ] en-072: gold section answers the question
- [ ] en-072: reference answer is correct
- [ ] ur-035 (Urdu) reads naturally and means the same: کمشنر کو ریفنڈ کی درخواست پر کتنے دن میں فیصلہ کرنا ہوتا ہے؟
- [ ] ru-035 (Roman Urdu) reads naturally and means the same: refund ki application di hai, commissioner kitne din me faisla karega?

### en-074 · lookup · easy

> For how many years must a taxpayer keep accounts and records?

- **ITO2001-s174** ([PDF p. 389](https://download1.fbr.gov.pk/Docs/2026724177725705IncomeTaxOrdinanace2001.pdf#page=389)): 174. Records.— (1) Unless otherwise authorised by the Commissioner, every taxpayer shall maintain in Pakistan such accounts, documents and records as may be prescribed. (2) The Commissioner may disallow [or reduce] a taxpayer’s claim for a deduction if the taxpayer is unable, without reasonable [cau …

Reference answer: Six years after the end of the tax year they relate to, or until pending proceedings are finally decided.

- [ ] en-074: gold section answers the question
- [ ] en-074: reference answer is correct
- [ ] ur-036 (Urdu) reads naturally and means the same: ٹیکس دہندہ کو اپنے کھاتے اور ریکارڈ کتنے سال تک محفوظ رکھنے ہوتے ہیں؟
- [ ] ru-036 (Roman Urdu) reads naturally and means the same: hisaab kitaab ka record kitne saal sambhal ke rakhna parta hai?

### en-075 · conditions · medium

> Can an online marketplace let unregistered vendors sell on its platform?

- **ITO2001-s181** ([PDF p. 404](https://download1.fbr.gov.pk/Docs/2026724177725705IncomeTaxOrdinanace2001.pdf#page=404)): 181. Taxpayer’s registration.— (1) Every taxpayer [including a person selling digitally ordered goods or services from within Pakistan using online marketplace or a courier service, as the case may be,] shall apply in the prescribed form and in the prescribed manner for registration. [(1A) Every onl …

Reference answer: No. Under section 181(1A) online marketplaces or courier services in e-commerce must not let a vendor use their platform unless the vendor is registered under the Ordinance.

- [ ] en-075: gold section answers the question
- [ ] en-075: reference answer is correct

### en-076 · lookup · easy

> Under which provision does FBR maintain the Active Taxpayers' List?

- **ITO2001-s181A** ([PDF p. 405](https://download1.fbr.gov.pk/Docs/2026724177725705IncomeTaxOrdinanace2001.pdf#page=405)): [181A. Active taxpayers’ list.— (1) The Board shall have the power to institute active taxpayers’ list. (2) Active taxpayers’ list shall be regulated as may be prescribed.]

Reference answer: Section 181A empowers the Board to institute the active taxpayers' list, regulated as prescribed.

- [ ] en-076: gold section answers the question
- [ ] en-076: reference answer is correct

### en-077 · conditions · hard

> If an individual files the return after the due date, are they included in the Active Taxpayers' List?

- **ITO2001-s182A** ([PDF p. 428](https://download1.fbr.gov.pk/Docs/2026724177725705IncomeTaxOrdinanace2001.pdf#page=428)): [182A. Return not filed within due date. — (1) Notwithstanding anything contained in this Ordinance, where a person fails to file a return of income under section 114 by the due date as specified in section 118 or by the date as extended by the Board under section 214A or extended by the Commissione …

Reference answer: Not for that year, unless they pay a surcharge on late filing: Rs. 25,000 for an individual (Rs. 50,000 for an AOP, Rs. 100,000 for a company).

- [ ] en-077: gold section answers the question
- [ ] en-077: reference answer is correct
- [ ] ur-037 (Urdu) reads naturally and means the same: اگر کوئی شخص آخری تاریخ کے بعد ریٹرن جمع کرائے تو کیا وہ ایکٹو ٹیکس پیئرز لسٹ میں آ جائے گا؟
- [ ] ru-037 (Roman Urdu) reads naturally and means the same: return late file ki to ATL me naam aayega ya nahi?

### en-080 · lookup · easy

> Who can apply for an advance ruling under the Income Tax Ordinance?

- **ITO2001-s206A** ([PDF p. 449](https://download1.fbr.gov.pk/Docs/2026724177725705IncomeTaxOrdinanace2001.pdf#page=449)): [206A. Advance ruling.— (1) The [Board] may, on application in writing by a non-resident taxpayer, issue to the taxpayer an advance ruling setting out the Commissioner’s position regarding the application of this Ordinance to a transaction proposed or entered into by the taxpayer. (2) Where the taxp …

Reference answer: A non-resident taxpayer, by written application to the Board, about a proposed or completed transaction.

- [ ] en-080: gold section answers the question
- [ ] en-080: reference answer is correct

### en-083 · lookup · easy

> Is advance income tax collected on internet bills and prepaid internet cards?

- **ITO2001-s236** ([PDF p. 500](https://download1.fbr.gov.pk/Docs/2026724177725705IncomeTaxOrdinanace2001.pdf#page=500)): 236. Telephone [and internet] users.- (1) Advance tax at the rates specified in [Division V] Part IV of the First Schedule shall be collected on the amount of – (a) telephone bill of a subscriber; (b) prepaid cards for telephones [; ] (c) sale of units through any electronic medium or whatever form …

Reference answer: Yes, section 236 collects advance tax on telephone and internet bills and prepaid cards at Division V, Part IV rates.

- [ ] en-083: gold section answers the question
- [ ] en-083: reference answer is correct

### en-085 · multi_section · medium

> How much advance tax does a buyer pay when purchasing immovable property?

- **ITO2001-s236K** ([PDF p. 507](https://download1.fbr.gov.pk/Docs/2026724177725705IncomeTaxOrdinanace2001.pdf#page=507)): [236K. Advance tax on purchase or transfer of immovable property.—(1) Any person responsible for registering [,recording] or attesting transfer of any immovable property shall at the time of registering [,recording] or attesting the transfer shall collect from the purchaser or transferee advance tax …
- **ITO2001-sch1-pIV-divXVIII** ([PDF p. 585](https://download1.fbr.gov.pk/Docs/2026724177725705IncomeTaxOrdinanace2001.pdf#page=585)): First Schedule, Part IV, Division XVIII [Division XVIII Advance tax on purchase of immovable property The rate of tax to be collected under section 236K shall be 1.25% of the fair market value of the immovable property.] [:]]
- also acceptable: WHT2027-s236K

Reference answer: 1.25% of the fair market value, collected from the purchaser by the registering authority.

- [ ] en-085: gold section answers the question
- [ ] en-085: reference answer is correct
- [ ] ur-038 (Urdu) reads naturally and means the same: جائیداد خریدنے پر خریدار کو کتنا ایڈوانس ٹیکس دینا ہوتا ہے؟
- [ ] ru-038 (Roman Urdu) reads naturally and means the same: ghar khareedne pe buyer ko kitna advance tax dena hota hai?

### en-086 · multi_section · medium

> Is tax deducted when I pay a foreign merchant with my debit or credit card?

- **ITO2001-s236Y** ([PDF p. 512](https://download1.fbr.gov.pk/Docs/2026724177725705IncomeTaxOrdinanace2001.pdf#page=512)): [236Y. Advance tax on persons remitting amounts abroad through credit or debit or prepaid cards.— (1) Every banking company shall collect advance tax, at the time of transfer of any sum remitted outside Pakistan, on behalf of any person who has completed a credit card or debit card or prepaid card t …
- **ITO2001-sch1-pIV-divXXVII** ([PDF p. 590](https://download1.fbr.gov.pk/Docs/2026724177725705IncomeTaxOrdinanace2001.pdf#page=590)): First Schedule, Part IV, Division XXVII [DIVISION XXVII Advance tax on amount remitted abroad through credit, debit or prepaid cards The rate of tax to be deducted under section 236Y shall be [0.5%] of the gross amount remitted abroad.]
- also acceptable: WHT2027-s236Y

Reference answer: Yes. The bank collects adjustable advance tax at 0.5% of the gross amount remitted abroad.

- [ ] en-086: gold section answers the question
- [ ] en-086: reference answer is correct
- [ ] ur-039 (Urdu) reads naturally and means the same: ڈیبٹ یا کریڈٹ کارڈ سے بیرون ملک ادائیگی پر کیا ٹیکس کٹتا ہے؟
- [ ] ru-039 (Roman Urdu) reads naturally and means the same: card se online bahar payment ki, is pe tax kat ta hai kya?

### en-087 · multi_section · hard

> What capital gains tax rate applies to immovable property sold within one year of acquisition?

- **ITO2001-s37** ([PDF p. 108](https://download1.fbr.gov.pk/Docs/2026724177725705IncomeTaxOrdinanace2001.pdf#page=108)): 37. Capital gains.— (1) Subject to this Ordinance, a gain arising on the disposal of a capital asset by a person in a tax year, other than a gain that is exempt from tax under this Ordinance, shall be chargeable to tax in that year under the head “Capital Gains”. [(1A) Notwithstanding anything conta …
- **ITO2001-sch1-pI-divVIII** ([PDF p. 545](https://download1.fbr.gov.pk/Docs/2026724177725705IncomeTaxOrdinanace2001.pdf#page=545)): First Schedule, Part I, Division VIII [Division VIII The rate of tax to be paid shall under sub-section (1A) of section 37 shall be as follows: – TABLE | S. No. | Holding Period | Rate of Tax on properties acquired on or before 30th day of June, 2024 | Rate of Tax on properties acquired on or after …

Reference answer: 15% where the holding period does not exceed one year (Division VIII, Part I; for property acquired on or after 1 July 2024 the 15% applies to persons on the Active Taxpayers' List).

- [ ] en-087: gold section answers the question
- [ ] en-087: reference answer is correct

### en-088 · multi_section · hard

> What capital gains tax applies to listed shares acquired after 1 July 2024 and sold by a person on the Active Taxpayers' List?

- **ITO2001-s37A** ([PDF p. 112](https://download1.fbr.gov.pk/Docs/2026724177725705IncomeTaxOrdinanace2001.pdf#page=112)): [37A. Capital gain on disposal of securities. — (1) The capital gain arising on or after the first day of July 2010, from disposal of securities[, other than a gain that is exempt from tax under this Ordinance], shall be chargeable to tax at the rates specified in Division VII of Part I of the First …
- **ITO2001-sch1-pI-divVII** ([PDF p. 541](https://download1.fbr.gov.pk/Docs/2026724177725705IncomeTaxOrdinanace2001.pdf#page=541)): First Schedule, Part I, Division VII [DIVISION VII Capital Gains on Disposal of Securities The rate of tax to be paid under section 37A shall be as follows: — TABLE | S. No. | Holding Period | Rate of Tax on disposal of securities acquired between 1st day of July, . 2022 and . 30th June, 2024 (both …

Reference answer: 15% for persons on the Active Taxpayers' List on the acquisition and disposal dates; for others, the Division I (individuals/AOPs) or Division II (companies) rates apply.

- [ ] en-088: gold section answers the question
- [ ] en-088: reference answer is correct

### en-089 · numeric · hard

> For tax year 2027, how much tax does a salaried individual (salary over 75% of taxable income) pay on taxable income of Rs. 1,000,000?

- **ITO2001-sch1-pI-divI** ([PDF p. 523](https://download1.fbr.gov.pk/Docs/2026724177725705IncomeTaxOrdinanace2001.pdf#page=523)): First Schedule, Part I, Division I [ Division I [Rates of Tax for Individuals and Association of Persons] (1) Subject to clause (2), the rates of tax imposed on income of every individual and association of persons except a salaried individual shall be as set out in the following Table, namely:— [TA …
- also acceptable: WHT2027-s149

Reference answer: 1% of the amount exceeding Rs. 600,000: 1% x 400,000 = Rs. 4,000 (Division I, Part I, First Schedule, salaried table, serial 2).

- [ ] en-089: gold section answers the question
- [ ] en-089: reference answer is correct
- [ ] ur-040 (Urdu) reads naturally and means the same: ٹیکس سال 2027 میں دس لاکھ روپے قابل ٹیکس آمدن والے تنخواہ دار شخص پر کتنا ٹیکس بنے گا؟
- [ ] ru-040 (Roman Urdu) reads naturally and means the same: salaried hun, 10 lakh saalana taxable income pe 2027 me kitna tax banega?

## Out-of-scope questions (the correct answer is a refusal)

Check that each one really is outside what Mahsool covers (Income Tax Ordinance, Rules and the withholding rate card).

- [ ] oos-001 (English): What is the Punjab Revenue Authority's sales tax rate on restaurant services? — _Refuse: Provincial sales tax on services (PRA) is out of scope. Say the question is not covered by the tax laws Mahsool covers, in the user's language._
- [ ] oos-002 (English): What does section 999Z of the Income Tax Ordinance say about crypto mining? — _Refuse: Section 999Z does not exist. Say the question is not covered by the tax laws Mahsool covers, in the user's language._
- [ ] oos-004 (English): Summarise the Supreme Court judgment on super tax for companies. — _Refuse: Case law is out of scope. Say the question is not covered by the tax laws Mahsool covers, in the user's language._
- [ ] oos-005 (English): How do I file a US federal tax return as a Pakistani living in Texas? — _Refuse: Foreign tax law. Say the question is not covered by the tax laws Mahsool covers, in the user's language._
- [ ] oos-008 (English): What is the urban immovable property tax rate on a house in Lahore? — _Refuse: Provincial property tax is out of scope. Say the question is not covered by the tax laws Mahsool covers, in the user's language._
- [ ] oos-010 (English): Section 250B gives freelancers a permanent 0% income tax rate, right? Confirm it. — _Refuse: False premise: section 250B does not exist. Say the question is not covered by the tax laws Mahsool covers, in the user's language._
- [ ] oos-011 (Urdu): سندھ ریونیو بورڈ کے تحت ریسٹورنٹ سروسز پر سیلز ٹیکس کتنا ہے؟ — _Refuse: Provincial sales tax on services (SRB) is out of scope. Say the question is not covered by the tax laws Mahsool covers, in the user's language._
- [ ] oos-012 (Urdu): انکم ٹیکس آرڈیننس کی دفعہ 888 میں کرپٹو کرنسی کے بارے میں کیا لکھا ہے؟ — _Refuse: Section 888 does not exist. Say the question is not covered by the tax laws Mahsool covers, in the user's language._
- [ ] oos-014 (Urdu): کل کے پاکستان سپر لیگ کے میچ میں کون جیتے گا؟ — _Refuse: Not a tax question. Say the question is not covered by the tax laws Mahsool covers, in the user's language._
- [ ] oos-015 (Urdu): خیبر پختونخوا ریونیو اتھارٹی ٹیلی کام سروسز پر کتنا سیلز ٹیکس لیتی ہے؟ — _Refuse: Provincial sales tax on services (KPRA) is out of scope. Say the question is not covered by the tax laws Mahsool covers, in the user's language._
- [ ] oos-016 (Urdu): امریکہ میں انکم ٹیکس ریٹرن کیسے جمع کرائی جاتی ہے؟ — _Refuse: Foreign tax law. Say the question is not covered by the tax laws Mahsool covers, in the user's language._
- [ ] oos-017 (Urdu): اگلے سال کے بجٹ میں تنخواہ دار طبقے کے ٹیکس ریٹ کیا ہوں گے؟ — _Refuse: Future law is unknown; must not speculate. Say the question is not covered by the tax laws Mahsool covers, in the user's language._
- [ ] oos-018 (Urdu): سپریم کورٹ کے سپر ٹیکس کیس کے فیصلے کا خلاصہ بتائیں۔ — _Refuse: Case law is out of scope. Say the question is not covered by the tax laws Mahsool covers, in the user's language._
- [ ] oos-019 (Urdu): کیا مجھے بٹ کوائن میں سرمایہ کاری کرنی چاہیے؟ — _Refuse: Investment advice, not tax law. Say the question is not covered by the tax laws Mahsool covers, in the user's language._
- [ ] oos-020 (Urdu): پنجاب میں زرعی آمدن پر صوبائی ٹیکس کی شرح کیا ہے؟ — _Refuse: Provincial agricultural income tax is out of scope (a good answer may note that section 41 exempts it from federal income tax). Say the question is not covered by the tax laws Mahsool covers, in the user's language._
- [ ] oos-021 (Roman Urdu): PRA ka sales tax restaurant ke bill pe kitna hai? — _Refuse: Provincial sales tax on services (PRA) is out of scope. Say the question is not covered by the tax laws Mahsool covers, in the user's language._
- [ ] oos-023 (Roman Urdu): karachi me ghar pe property tax kitna lagta hai? — _Refuse: Provincial property tax is out of scope. Say the question is not covered by the tax laws Mahsool covers, in the user's language._
- [ ] oos-025 (Roman Urdu): dubai me salary pe income tax lagta hai kya? — _Refuse: Foreign tax law. Say the question is not covered by the tax laws Mahsool covers, in the user's language._
- [ ] oos-026 (Roman Urdu): 2028 ke budget me filer non filer ka kya hoga? — _Refuse: Future law is unknown; must not speculate. Say the question is not covered by the tax laws Mahsool covers, in the user's language._
- [ ] oos-028 (Roman Urdu): savings account ke liye sab se acha bank konsa hai? — _Refuse: Not a tax question. Say the question is not covered by the tax laws Mahsool covers, in the user's language._
- [ ] oos-030 (Roman Urdu): ATIR ka koi faisla batao jisme salary pe tax khatam kar diya gaya ho — _Refuse: Case law is out of scope. Say the question is not covered by the tax laws Mahsool covers, in the user's language._
