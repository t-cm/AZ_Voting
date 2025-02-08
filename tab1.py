import streamlit as st
import pandas as pd
import random
import uuid
import re
from data import generate_data  

# # --------------------------------------------------
# # Main app function
# # --------------------------------------------------
def app():

    st.title("Voter Search")

    # Load the data from macrodata.csv
    df = generate_data()
    ##############################################
    # SIMPLE SEARCH FUNCTIONS
    ##############################################

    # Free-text search: matches all tokens in each row.
    def filter_data_by_query(df, query):
        tokens = query.lower().split()
        return df[df.apply(lambda row: all(token in " ".join(row.astype(str)).lower() for token in tokens), axis=1)]


    def parse_graphql_query(query, df):
        q = " ".join(query.split())
        pat = r'people\s*\(\s*where\s*:\s*{(.*?)}\s*\)\s*{(.*?)}'
        m = re.search(pat, q)
        if not m:
            raise ValueError("GraphQL query format not recognized.")
        cond_str, sel_str = m.group(1).strip(), m.group(2).strip()
        conds = re.findall(r'(\w+)\s*:\s*"([^"]+)"', cond_str)
        parsed = []
        for field, value in conds:
            if field.endswith("_startsWith"):
                parsed.append((field[:-len("_startsWith")], "startsWith", value))
            else:
                parsed.append((field, "=", value))
        # Map GraphQL field names to our DataFrame columns (new schema)
        gql2df = {
            "firstName": "First Name -MyData",
            "lastName": "Last Name -MyData",
            "phone": "Phone",
            "phoneType": "Phone Type",
            "landlinePhone": "Landline Phone",
            "cellPhone": "Cell Phone",
            "email": "Email -MyData",
            "address": "Address -MyData",
            "addressLine2": "Address Line 2 -MyData",
            "city": "City -MyData",
            "county": "County",
            "state": "State -MyData.",
            "zip": "Zip –MyData",
            "registrationStatus": "Registration Status",
            "registrationDate": "Registration Date",
            "voterStatus": "Voter Status",
            "party": "Party",
            "gender": "Gender -MyData",
            "township": "Township",
            "officialCongressionalDistricts": "Official Congressional Districts",
            "officialStateSenateDistricts": "Official State Senate Districts",
            "officialStateHouseDistrict": "Official State House District",
            "uid": "uid"
        }
        mask = pd.Series(True, index=df.index)
        for field, op, value in parsed:
            # Look up by mapping; if not found, try a generic lower-case key match.
            df_field = gql2df.get(field) or {c.lower().replace(" ", "").replace("-", ""): c for c in df.columns}.get(field.lower())
            if not df_field:
                continue
            if op == "=":
                mask &= df[df_field].astype(str).str.lower().eq(value.lower())
            elif op == "startsWith":
                mask &= df[df_field].astype(str).str.lower().str.startswith(value.lower())
        filt = df[mask]
        selected = [s.strip() for s in sel_str.split() if s.strip()]
        sel_fields = []
        for s in selected:
            mapped = gql2df.get(s) or {c.lower().replace(" ", "").replace("-", ""): c for c in df.columns}.get(s.lower())
            if mapped:
                sel_fields.append(mapped)
        if not sel_fields:
            sel_fields = df.columns.tolist()
        return filt, sel_fields

    def parse_sql_query(query, df):
        q = " ".join(query.split())
        # Updated regex pattern to allow an optional LIMIT clause.
        pat = r"SELECT\s+(.+?)\s+FROM\s+people(?:\s+WHERE\s+(.+?))?(?:\s+LIMIT\s+(\d+))?;?\s*$"
        m = re.search(pat, q, re.IGNORECASE)
        if not m:
            raise ValueError("SQL query format not recognized.")
        cols_str = m.group(1).strip()
        where_str = m.group(2).strip() if m.group(2) else ""
        limit_str = m.group(3).strip() if m.group(3) else ""

        # Map SQL field names to CSV columns (new schema)
        sql2df = {
            "firstname": "First Name -MyData",
            "lastname": "Last Name -MyData",
            "phone": "Phone",
            "phonetype": "Phone Type",
            "landlinephone": "Landline Phone",
            "cellphone": "Cell Phone",
            "email": "Email -MyData",
            "address": "Address -MyData",
            "addressline2": "Address Line 2 -MyData",
            "city": "City -MyData",
            "county": "County",
            "state": "State -MyData.",
            "zip": "Zip –MyData",
            "registrationstatus": "Registration Status",
            "registrationdate": "Registration Date",
            "voterstatus": "Voter Status",
            "party": "Party",
            "gender": "Gender -MyData",
            "township": "Township",
            "officialcongressionaldistricts": "Official Congressional Districts",
            "officialstatesenatedistricts": "Official State Senate Districts",
            "officialstatehousedistrict": "Official State House District",
            "uid": "uid"
        }

        if cols_str == "*":
            sel_fields = df.columns.tolist()
        else:
            sel_fields = []
            for col in cols_str.split(","):
                col = col.strip()
                mapped = sql2df.get(col.lower()) or {c.lower().replace(" ", "").replace("-", ""): c for c in df.columns}.get(col.lower())
                if mapped:
                    sel_fields.append(mapped)
            if not sel_fields:
                sel_fields = df.columns.tolist()

        mask = pd.Series(True, index=df.index)
        if where_str:
            # Split conditions by AND.
            conds = re.split(r'\s+AND\s+', where_str, flags=re.IGNORECASE)
            for cond in conds:
                m_cond = re.match(r"(\w+)\s*(=|LIKE)\s*'([^']+)'", cond, re.IGNORECASE)
                if m_cond:
                    field, op, value = m_cond.groups()
                    df_field = sql2df.get(field.lower()) or {c.lower().replace(" ", "").replace("-", ""): c for c in df.columns}.get(field.lower())
                    if not df_field:
                        continue
                    if op == "=":
                        mask &= df[df_field].astype(str).str.lower().eq(value.lower())
                    elif op.upper() == "LIKE":
                        val = value.lower()
                        if val.startswith("%") and val.endswith("%"):
                            mask &= df[df_field].astype(str).str.lower().str.contains(val.strip("%"))
                        elif val.endswith("%"):
                            mask &= df[df_field].astype(str).str.lower().str.startswith(val.rstrip("%"))
                        elif val.startswith("%"):
                            mask &= df[df_field].astype(str).str.lower().str.endswith(val.lstrip("%"))
                        else:
                            mask &= df[df_field].astype(str).str.lower().eq(val)
                else:
                    st.warning(f"Invalid condition: {cond}")

        result_df = df[mask]
        # If a LIMIT clause is provided, reduce the number of rows returned.
        if limit_str:
            try:
                limit_val = int(limit_str)
                result_df = result_df.head(limit_val)
            except Exception as e:
                st.warning("Invalid limit value, ignoring limit.")

        return result_df, sel_fields

    ##############################################
    # UI: Query Input & Results Display
    ##############################################

    st.markdown("### Enter Your Query")
    st.info(
        "Enter a query in one of these formats:\n\n"
        "1. **Natural Language** (free text, e.g., `John`)\n"
        "2. **GraphQL** (start with `{`, see example below)\n"
        "3. **SQL** (start with `SELECT`, see example below)"
    )

    with st.expander("GraphQL Query Example"):
        st.code(
        """{
        people(where: {
            firstName: "John",
            city: "Mesa"
        }) {
            firstName
            lastName
            city
            address
            state
            registrationDate
            voterStatus
        }
        }
        """,
        language='graphql'
        )

    with st.expander("SQL Query Example"):
        st.code(
        """SELECT firstName, lastName, address, registrationDate, voterStatus
        FROM people
        WHERE firstName = 'John'
        AND city LIKE '%Tucson%'
        AND address LIKE '%Park%'
        LIMIT 50
        """,
        language='sql'
        )
    
    query = st.text_area("Search Query", height=150, placeholder="Enter your query here...")

    if st.button("Run Query"):
        if query:
            if query.strip().startswith("{"):
                try:
                    filt, sel = parse_graphql_query(query, df)
                    st.write(f"GraphQL Query – Found {len(filt)} entries")
                    st.dataframe(filt[sel])
                except Exception as e:
                    st.error(f"Error: {e}")
            elif query.strip().upper().startswith("SELECT"):
                try:
                    filt, sel = parse_sql_query(query, df)
                    st.write(f"SQL Query – Found {len(filt)} entries")
                    st.dataframe(filt[sel])
                except Exception as e:
                    st.error(f"Error: {e}")
            else:
                filt = filter_data_by_query(df, query)
                st.write(f"Found {len(filt)} entries")
                st.dataframe(filt)
        else:
            st.info("Enter a search query above to filter data.")
