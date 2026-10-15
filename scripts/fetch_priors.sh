#!/usr/bin/env bash
# Prior-knowledge resources (licences checked: see reports/priors.md) -> $DATA/priors/<resource>/,
# mirrored to gdrive:VCC2026/data/priors. Run inside tmux; log: logs/data_priors.log
source ~/.vcc_env; cd ~/vcc
P=$DATA/priors; log=logs/data_priors.log; mkdir -p $P
say() { echo "[$(date -u +%FT%TZ)] $*" | tee -a $log; }
get() {  # get <resource> <url> [outname]
  local d=$P/$1 out=${3:-$(basename "${2%%\?*}")}; mkdir -p $d
  for t in 1 2 3 4 5; do wget -q -c -O "$d/$out" "$2" && break; sleep 10; done
  [ -s "$d/$out" ] && say "got $1/$out $(du -h "$d/$out" | cut -f1)" || say "FAILED $1 $2"
}
say "start"
S=https://stringdb-downloads.org/download
get string $S/protein.links.detailed.v12.0/9606.protein.links.detailed.v12.0.txt.gz
get string $S/protein.info.v12.0/9606.protein.info.v12.0.txt.gz
get string $S/protein.aliases.v12.0/9606.protein.aliases.v12.0.txt.gz
get go http://current.geneontology.org/annotations/goa_human.gaf.gz
get go http://purl.obolibrary.org/obo/go/go-basic.obo
U=https://ftp.uniprot.org/pub/databases/uniprot/current_release/knowledgebase/reference_proteomes/Eukaryota/UP000005640
get uniprot $U/UP000005640_9606.fasta.gz
get uniprot $U/UP000005640_9606.idmapping.gz
curl -sI https://rest.uniprot.org/uniprotkb/P05412 | grep -i '^x-uniprot-release' > $P/uniprot/RELEASE.txt
get depmap https://ndownloader.figshare.com/files/51064667 CRISPRGeneEffect.csv
get depmap https://ndownloader.figshare.com/files/51065297 Model.csv
get depmap https://ndownloader.figshare.com/files/51065795 README.txt
R=https://reactome.org/download/current
get reactome $R/ReactomePathways.gmt.zip
get reactome $R/ReactomePathways.txt
get reactome $R/ReactomePathwaysRelation.txt
get reactome $R/Ensembl2Reactome.txt
curl -s https://reactome.org/ContentService/data/database/version > $P/reactome/VERSION.txt
# CollecTRI (TF->target) is NOT fetched: it is a composite of databases with their own licences, and
# OmniPath's license=commercial filter returned the identical row set (64,516) on 15 Oct 2026, so
# commercial use could not be verified. See reports/priors.md.
rclone copy $P gdrive:VCC2026/data/priors >> $log 2>&1 && rclone check --size-only $P gdrive:VCC2026/data/priors >> $log 2>&1 \
  && say "drive copy OK" || say "FAILED drive copy"
say "done $(du -sh $P | cut -f1)"
