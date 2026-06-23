import pandas as pd
import re
from pathlib import Path
import argparse


def argMain():
    parser = argparse.ArgumentParser(description="Extract log templates and structured logs")
    
    # Dataset name:
    parser.add_argument(
        "-d", 
        "--ds_name",
        dest="d",
        type=str, 
        default="all", 
        help="Dataset name")
    
    # Output directory:    
    parser.add_argument(
        "-o",
        "--output",
        dest="o",
        type=str,
        default="data_prc",
        help="Thư mục output"
    )
    
    # Max uniques to representation template example in file:
    parser.add_argument(
        "-u",
        "--max_uni",
        dest="u",
        type=int,
        default=None,
        help="Max unique logs"
    )
    
    args = parser.parse_args()
    
    data_path = Path("../data/")
    all_ds = {
        f.name.lower(): f.name
        for f in data_path.iterdir()
        if f.is_dir()
    }
    DS_LST = []
    
    if args.d.lower() == "all":
        DS_LST = sorted(all_ds.values())
    else:
        ds_request = [
            ds.strip().lower()
            for ds in args.d.split(",") if ds.strip().lower() in all_ds    
        ]
        
        none_ds = set([ds.strip().lower() for ds in args.d.split(",")]) - set(all_ds.keys())
        if none_ds:
            print(f"Warning: Dataset {', '.join(none_ds)} not found!")

        DS_LST = [all_ds[ds] for ds in ds_request]

    return {
        "DS_LST": DS_LST,
        "OUT_DIR": Path(args.o),
        "MAX_UNI": args.u
    }

def tpl2rex(tpl):
    tpl_rex = re.sub(r"<.{1,5}>", "<*>", tpl)
    tpl_rex = re.sub(r"([^A-Za-z0-9])", r"\\\1", tpl_rex)
    tpl_rex = re.sub(r"\\ +",           r"\\s+", tpl_rex)
    tpl_rex = ("^" +tpl_rex.replace(r"\<\*\>", "(.*?)") + "$")

    return re.compile(tpl_rex)

def createNumUniCol(temp_df=None, stru_df=None):
    if temp_df is None or stru_df is None:
        return None
    else:
        unique_counts = (
            stru_df.groupby("EventId")["Content"]
                .nunique()
                .to_dict()
        )
        temp_df["NumUniques"] = temp_df["EventId"].map(unique_counts).fillna(0).astype(int)

        temp_df["NumofParams"] = (
            temp_df["EventTemplate"]
                .astype(str)
                .str.count(r"<\*>")
        )
    return temp_df

def tempExt(temp_path=None, stru_path=None, out_dir=None, max_uni=30):
    temp_df = pd.read_csv(temp_path)
    stru_df = pd.read_csv(stru_path)
    
    temp_df = createNumUniCol(temp_df, stru_df)
    
    for idx, tpl_row in temp_df.iterrows():
        eid   = tpl_row["EventId"]
        e_tpl = tpl_row["EventTemplate"]
        occur = tpl_row["Occurrences"]
        
        regex = tpl2rex(e_tpl)
        
        logs  = stru_df.loc[stru_df["EventId"] == eid, "Content"]
        uni_logs  = logs.unique().tolist()
        temp_df.loc[idx, "NumUniques"] = len(uni_logs)
        
        out_file = Path(out_dir / f"{eid}.txt")
        with open(out_file, "w", encoding="utf-8") as f:
            f.write(f"EventId: {eid}\n")
            f.write(f"EventTemplate: {e_tpl}\n")
            f.write(f"Occurrences: {occur}\n\n")
            f.write(f"Nums of unique: {len(uni_logs)}\n")
            
            f.write(f"Example sample logs (<{max_uni}): \n")

            for i, log in enumerate(uni_logs):
                m = regex.match(log)
                if m:
                    params = list(m.groups())
                else: 
                    params = []
                    
                line = log + "\t"
                for p in params:
                    line += f"|{p}"
                f.write(line + "\n")
                
                if i >= max_uni: 
                    break
    out_csv = "_" + temp_path.stem + "_stats.csv"
    out_csv = out_dir / out_csv
    
    temp_df = temp_df.sort_values(
        by=["Occurrences", "NumUniques", "NumofParams"],
        ascending=False
    )

    temp_df.to_csv(out_csv, index=False)


def main():
    args = argMain()
    
    # ===================== CONFIG PARAM ====================
    DS_LST = args["DS_LST"]
    OUT = args["OUT_DIR"]
    MAX_UNI = args["MAX_UNI"]
    # =======================================================

    for DS in DS_LST:
        print("Processing dataset: ", DS)
        RAWL_PATH = Path(f"../data/{DS}/{DS}_full.log")
        TEMP_PATH = Path(f"../data/{DS}/{DS}_full.log_templates.csv")
        STRU_PATH = Path(f"../data/{DS}/{DS}_full.log_structured.csv")
        
        OUT_DIR = OUT / DS
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        tempExt(
            temp_path=TEMP_PATH,
            stru_path=STRU_PATH,
            out_dir=OUT_DIR,
            max_uni=MAX_UNI
        )
     
if __name__ == "__main__":
    main()