import argparse
from collections import namedtuple
import csv
import datetime
from decimal import Decimal
from enum import Enum


_QifEntryTuple = namedtuple(
    'QifEntryTuple',
    ['date', 'amount', 'payee', 'memo'],
)


class QifEntry(_QifEntryTuple):
    __slots__ = ()

    def serialize(self):
        lines = list()
        lines.append("T" + str(self.amount))
        lines.append("D" + self.date.strftime("%m/%d/%Y"))
        lines.append("P" + str(self.payee))
        lines.append("M" + str(self.memo))
        lines.append("^")
        return "\n".join(lines)


class InOut(Enum):
    IN = 1
    OUT = 2


_IngEntryTuple = namedtuple(
    'IngEntryTuple',
    ['date', 'description', 'account',
     'counter_party_account', 'code', 'in_out', 'amount', 'category', 'memo'],
)


class IngEntry(_IngEntryTuple):
    __slots__ = ()

    def to_qif(self):
        amount = self.amount
        if self.in_out == InOut.OUT:
            amount = -amount

        return QifEntry(
            date=self.date,
            amount=amount,
            memo=self.memo,
            payee=self.description
        )


class IngCsvFileReader():

    def __init__(self, file):
        self.file = csv.DictReader(file)

    def parse_in_out(self, s):
        if s == "Af":
            return InOut.OUT
        elif s == "Bij":
            return InOut.IN
        else:
            raise Exception("Expected 'Af' or 'Bij'")

    def parse_amount(self, s):
        return Decimal(s.replace(",", "."))

    def parse_date(self, s):
        return datetime.datetime.strptime(s, "%Y%m%d").date()

    def __iter__(self):
        return self

    def __next__(self):
        d = next(self.file)
        return IngEntry(
            date=self.parse_date(d["Datum"]),
            description=d["Naam / Omschrijving"],
            account=d["Rekening"],
            counter_party_account=d["Tegenrekening"],
            code=d["Code"],
            in_out=self.parse_in_out(d["Af Bij"]),
            amount=self.parse_amount(d["Bedrag (EUR)"]),
            category=d["Mutatiesoort"],
            memo=d["Mededelingen"],
        )


class QifFileWriter():

    def __init__(self, file):
        self.file = file
        self.write_header()

    def write_header(self):
        self.file.write('!Type:Bank\n')

    def write_entry(self, e):
        self.file.write(e.serialize())
        self.file.write("\n")


def convert_file(csv_path, qif_path):
    with open(csv_path) as csv_file, open(qif_path, 'w') as qif_file:
        qif_writer = QifFileWriter(qif_file)
        for ing_entry in IngCsvFileReader(csv_file):
            qif_writer.write_entry(ing_entry.to_qif())


if __name__ == '__main__':

    parser = argparse.ArgumentParser(
        description="Convert ING banking statements in CSV format to QIF file "
                    "for GnuCash."
    )
    parser.add_argument(
        "csvfile",
        help="The CSV file with banking statements"
    )
    parser.add_argument(
        "out",
        help="Output QIF file"
    )
    args = parser.parse_args()

    convert_file(args.csvfile, args.out)
