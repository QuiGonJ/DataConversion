#!/usr/bin/python
# Convert CSV from X to Cougar Mountain
#
# Notes:
#   1. GitHub wiki: https://github.com/QuiGonJ/DataConversion/wiki
#   2. Manual procedure: https://github.com/QuiGonJ/DataConversion/wiki/Cougar-Mountain-Transaction-Export-from-Donor-Perfect-Online(DPO)

#
# For transactions with header and footers means that for AR transactions
# the templates have to be split into two:  Detail and Header.  These will require key numbers and will be merged as
# Comma separated strings.
# The Strings will be merged and written out into a pseudo csv file.
#

#
# TODO:
#   - Remove left column and headers
#   - Add run log recording each conversion
#   - Integrate GUI
#   - Add hard coded source directory (Or find out from rick how to do a button gizmo)
#
import re
import tkinter as tk
from tkinter import filedialog
import pandas as pd
import os

# MASTER_CONVERSION_DIR = "C:\\Users\\DELL/\\Documents\\Conversion\\"
MASTER_CONVERSION_DIR = "C:\\Data\\Documents\\Conversion\\"
#
SOURCE = "Source\\"
TARGET = "Target\\"
TEMPLATES = "Templates\\"
#
SRC_DATA_DIR=MASTER_CONVERSION_DIR + SOURCE
TARGET_DATA_DIR=MASTER_CONVERSION_DIR + TARGET
TEMPLATES_DATA_DIR=MASTER_CONVERSION_DIR + TEMPLATES

def fileBaseOnly(path): return os.path.basename(path).split('.')[0]


class DPCustomerTransmuter:
    """Common base class for all employees"""
    convCount = 0

    def __init__(self, template, srcDataFile):
        self.templatePath = MASTER_CONVERSION_DIR + TEMPLATES + template
        self.srcDataPath = MASTER_CONVERSION_DIR + SOURCE + srcDataFile
        self.tgtDataPath = MASTER_CONVERSION_DIR + TARGET + fileBaseOnly(template) + '.txt'


    def load(self):

        self.templateSheet = pd.read_excel(self.templatePath, sheet_name='Sheet1', skiprows=0)
        self.templateCodes = pd.read_excel(self.templatePath, sheet_name='Delete this when done', skiprows=0)
        self.templateColumns = self.templateSheet.columns
        i = 0
        for col in self.templateSheet.columns:
            print(str(i) + " " + col)
            i += 1

        print("Template loaded: " + self.templatePath)
        # 'XXX Cougar Mountain - All Donor'
        # self.dpData = pd.read_excel(self.srcDataPath, sheet_name=0, skiprows=1, skipfooter=0).copy()
        self.dpData = pd.read_excel(self.srcDataPath, sheet_name=0, skiprows=0, skipfooter=0).copy()
        self.dpDataColumns = self.dpData.columns
        self.dpDataColumns = self.dpData.columns
        print("Data loaded")


    def build(self):

        def normalizedName(first, last):
            return (first + "" + last).strip()

        donorIdLabels = [id for id in self.dpData['Donor ID']]

        ids = [int(id) for id in self.dpData['Donor ID']]

        self.df = pd.DataFrame(index=range(0, len(ids)), columns=self.templateSheet.columns)

        dataLineCount = len(ids)
        self.df['Customer Number'] = pd.Series(ids)
        self.df['AR Code'] = pd.Series(dataLineCount * ["AR"])
        self.df['Customer Type'] = pd.Series(dataLineCount * [""])
        self.df['Customer Name'] = \
            self.dpData['First Name (FIRST_NAME)'] + " " + self.dpData['Last Name (LAST_NAME)']
        self.df['Customer Name'].str.strip()

        self.df['Billing Contact Name'] = self.dpData['Optional Line']
        self.df['Billing Address Line 1'] = self.dpData['Address']
        self.df['Billing Address Line 2'] = self.dpData['Address 2']
        self.df['Billing Address Line 1'].str.strip()
        self.df['Billing Address Line 2'].str.strip()

        self.df['Billing City'] = self.dpData['City']
        self.df['Billing State/Province'] = self.dpData['State']
        self.df['Billing Postal Code'] = self.dpData['Zip/Postal']
        self.df['Billing Counry'] = pd.Series(dataLineCount * ["United States"])

        self.df['Date Created'] = self.dpData['Created Date']
        self.df['EFT Customer Flag'] = 0

        self.df['UDF1'] = 0
        self.df['UDF2'] = 0
        self.df['UDF3'] = 0
        self.df['UDF4'] = 0
        self.df['UDF5'] = 0
        self.df['UDF6'] = 0
        self.df['UDF7'] = 0
        self.df['UDF8'] = 0
        self.df['UDF9'] = 0
        self.df['UDF10'] = 0

        self.df['Additional Date'] = self.dpData['Created Date']

        # Special cases:  Church names are "last name only."
        names = self.df['Customer Name']
        sourceLastNames = self.dpData['Last Name (LAST_NAME)']
        ix = 0
        for name in names:
            # make Church names look like human names
            if str(name).strip().lower() == "nan": # 'Not a Number' indicates empty field...
                churchName = str(sourceLastNames[ix])
                names[ix] = churchName
            # Names must be no more than 35 chars long
            if len(names[ix]) > 35:
                shortName = names[ix][0:35]
                names[ix] = shortName
            ix += 1

        self.df['Customer Name'] = names
        self.arCustomerListCsvOut = self.df.to_csv(index=False, sep='\t')

        with open(self.tgtDataPath, 'w+') as dst:
            dst.write(self.arCustomerListCsvOut)

        print('built')


class DPTransactionTransmuter:
    """Common base class for all employees"""
    convCount = 0

    def __init__(self, template, srcDataFile):
        self.templatePath = MASTER_CONVERSION_DIR + TEMPLATES + template
        self.srcDataPath = MASTER_CONVERSION_DIR + SOURCE + srcDataFile
        self.tgtDataPath = MASTER_CONVERSION_DIR + TARGET + fileBaseOnly(template) + '.txt'

    def load(self):

        self.headerTemplate = pd.read_excel(self.templatePath, sheet_name='Sheet1', skiprows=0, nrows=1)
        self.headerColumns = self.headerTemplate.columns

        self.detailTemplate = pd.read_excel(self.templatePath, sheet_name='Sheet1', skiprows=2, nrows=1)
        self.detailColumns = self.detailTemplate.columns

        print("Templates loaded (transaction)")

        self.dpData = pd.read_excel(self.srcDataPath, sheet_name=0, skiprows=1, skipfooter=0).copy()
        self.dpDataColumns = self.dpData.columns
        print("Data loaded: " + self.srcDataPath)


    def build(self):

        def reformStockCode(glNumber):
            #
            # Per stock code determination as explained by Rick Ridgway 19.7.24
            #
            try:
                # Check if digit is numeric
                magicDigit = int(glNumber[2])
                pass
            except ValueError:
                return "Unknown code for " + glNumber
            if magicDigit <= 1:
                magicDigit = 0
            tail = glNumber[-5:]
            # Replace last digit by new magic digit
            code = tail[:-1] + str(magicDigit)
            return code

        def normalizedName(first, last):
            if len(first) == 0:
                first = last
                last = ""
            return (first + "" + last).strip()

        ids = [int(id) for id in self.dpData['Donor ID']]

        self.headerFrame = pd.DataFrame(index=range(0, len(ids)), columns=self.headerColumns)
        self.detailFrame = pd.DataFrame(index=range(0, len(ids)), columns=self.detailColumns)
        dataLineCount = len(ids)
        glNumbers = [str(n) for n in self.dpData['General Ledger']]
        # Replace occurances of 7BL with 000 (Ref. R. Ridgway 2019.7.31)
        i = 0
        while i < dataLineCount:
            glNumbers[i] = glNumbers[i].replace('7BL','000')
            name = str(self.headerFrame['Shipping Address Contact'][i])
            if name == "" or name == 'nan':
                name = self.dpData['Last Name (LAST_NAME)'][i]
                name.strip()
                self.headerFrame['Shipping Address Contact'][i] = name
            i += 1
        stockCodes = [reformStockCode(n) for n in glNumbers]
        txnIds = ["{:03d}".format(value) for value in range(dataLineCount)]
        #
        # Header
        #

        # Using DataFrame.insert() to add a column
        self.headerFrame.insert(0, "Transaction Number", txnIds, True)
        #self.headerFrame['Transaction Number'] = list(range(len(ids)))
        self.headerFrame['Header Identifier'] = pd.Series(dataLineCount * ["1H"])
        self.headerFrame['Shipping Customer'] = self.dpData["Donor ID"]
        self.headerFrame['Shipping Address Contact'] = \
            self.dpData['First Name (FIRST_NAME)'] + " " + self.dpData['Last Name (LAST_NAME)']
        self.headerFrame['Shipping Address Contact'].str.strip()

        # For organization names (where no first name) use last name only.
        i = 0
        while i < dataLineCount:
            name = str(self.headerFrame['Shipping Address Contact'][i])
            if name == "" or name == 'nan':
                name = self.dpData['Last Name (LAST_NAME)'][i]
                name.strip()
                self.headerFrame['Shipping Address Contact'][i] = name
            i += 1

        self.headerFrame['Shipping Address Line 1'] = pd.Series(dataLineCount * [""])
        self.headerFrame['Shipping Address Line 2'] = pd.Series(dataLineCount * [""])
        self.headerFrame['Shipping Address City'] = pd.Series(dataLineCount * [""])
        self.headerFrame['Shipping Address State/Province'] = pd.Series(dataLineCount * [""])
        self.headerFrame['Shipping Address Postal Code'] = pd.Series(dataLineCount * [""])
        self.headerFrame['Shipping Address Counry'] = pd.Series(dataLineCount * [""])

        self.headerFrame['Cash/Check/CC/Chg'] = pd.Series(dataLineCount * ["0"])
        self.headerFrame['Transaction Type'] = pd.Series(dataLineCount * ["0"])

        self.headerFrame['Invoice Number'] = self.dpData['Reference / Check Number']
        # If check number is missing, use reference number instead.
        i = 0
        while i < dataLineCount:
            if str(self.headerFrame['Invoice Number'][i]) == "nan":
                self.headerFrame['Invoice Number'][i] = self.dpData['Reference Number'][i]
            i += 1

        self.headerFrame['PO Number'] = pd.Series(dataLineCount * [""])
        self.headerFrame['Ship Via Code'] = pd.Series(dataLineCount * [""])
        self.headerFrame['Department Code'] = stockCodes
        self.headerFrame['Saleperson Code'] = pd.Series(dataLineCount * [""])
        self.headerFrame['Sales Tax Code'] = pd.Series(dataLineCount * [""])
        self.headerFrame['Terms Code'] = pd.Series(dataLineCount * [""])
        self.headerFrame['Discount Code AR'] = pd.Series(dataLineCount * [""])
        self.headerFrame['Check Number'] = pd.Series(dataLineCount * [""])
        self.headerFrame['Check authorization'] = pd.Series(dataLineCount * [""])
        self.headerFrame['Check Account Number'] = pd.Series(dataLineCount * [""])
        self.headerFrame['Check Routing Number'] = pd.Series(dataLineCount * [""])
        self.headerFrame["Check Driver's Lic No"] = pd.Series(dataLineCount * [""])
        self.headerFrame['Credit Card Code'] = pd.Series(dataLineCount * [""])
        self.headerFrame['Credit Card Authorization'] = pd.Series(dataLineCount * [""])
        self.headerFrame['Invoice Date'] = self.dpData['Created Date']
        self.headerFrame['Order Date'] = pd.Series(dataLineCount * [""])
        self.headerFrame['Shipping Date'] = pd.Series(dataLineCount * [""])
        self.headerFrame['UDF1'] = pd.Series(dataLineCount * [""])
        self.headerFrame['UDF2'] = pd.Series(dataLineCount * [""])
        self.headerFrame['UDF3'] = pd.Series(dataLineCount * [""])
        self.headerFrame['UDF4'] = pd.Series(dataLineCount * [""])
        self.headerFrame['UDF5'] = pd.Series(dataLineCount * [""])
        self.headerFrame['Printed Flag'] = pd.Series(dataLineCount * [""])
        self.headerFrame['Shipping Phone'] = pd.Series(dataLineCount * [""])
        self.headerFrame['Shipping Fax'] = pd.Series(dataLineCount * [""])
        self.headerFrame['Payer'] = pd.Series(dataLineCount * [""])
        #
        # Detail
        #
        self.detailFrame.insert(0, "Transaction Number", txnIds, True)
        #self.detailFrame['Transaction Number'] = list(range(len(ids))) # pd.Series(ids)
        self.detailFrame['Detail Identifier'] = pd.Series(dataLineCount * ["2D"])
        self.detailFrame['Line Type'] = pd.Series(dataLineCount * ["1"])
        self.detailFrame['Stock/Code'] = stockCodes
        self.detailFrame['Stock Location'] = pd.Series(dataLineCount * [""])
        self.detailFrame['Description'] = self.dpData['General Ledger Descr']
        i = 0
        while i < dataLineCount:
            descr = str(self.detailFrame['Description'][i])
            if descr == "nan":
                alt = str(self.detailFrame['Stock/Code'][i])
                self.detailFrame['Description'][i] = alt.strip()
            i += 1

        self.detailFrame['Sales Dept Code'] = pd.Series(dataLineCount * [""])
        self.detailFrame['Salesperson Code'] = pd.Series(dataLineCount * [""])
        self.detailFrame['Sales Tax Code'] = pd.Series(dataLineCount * [""])
        self.detailFrame['Comment Code'] = pd.Series(dataLineCount * [""])
        self.detailFrame['Taxable'] = pd.Series(dataLineCount * ["0"])
        self.detailFrame['Promotion Code'] = pd.Series(dataLineCount * [""])
        self.detailFrame['Discount Code'] = pd.Series(dataLineCount * [""])
        self.detailFrame['Discount%'] = pd.Series(dataLineCount * [""])
        self.detailFrame['Quantity Ordered'] = pd.Series(dataLineCount * ["1"])
        self.detailFrame['Quantity Shipped'] = pd.Series(dataLineCount * ["1"])
        self.detailFrame['Quantity Backordered'] = pd.Series(dataLineCount * [""])
        # Unit price is Gift Amount but without dollar sign.
        i = 0
        while i < dataLineCount:
            unitPrice = str(self.dpData['Gift Amount'][i])
            self.detailFrame['Unit Price'][i] = unitPrice.replace('$', '', 1).replace(',', '', 1)
            i += 1

        self.detailFrame['Promotional Price'] = pd.Series(dataLineCount * [""])
        self.detailFrame['Serial Number'] = pd.Series(dataLineCount * [""])
        self.detailFrame['UDF1'] = pd.Series(dataLineCount * [""])
        self.detailFrame['UDF2'] = pd.Series(dataLineCount * [""])
        self.detailFrame['UDF3'] = pd.Series(dataLineCount * [""])
        self.detailFrame['UDF4'] = pd.Series(dataLineCount * [""])
        self.detailFrame['UDF5'] = pd.Series(dataLineCount * [""])
        self.detailFrame['Misc Price'] = pd.Series(dataLineCount * [""])
        self.detailFrame['For Lease'] = pd.Series(dataLineCount * [""])
        self.detailFrame['Term Start Date'] = pd.Series(dataLineCount * [""])
        self.detailFrame['Term Expiration Date'] = pd.Series(dataLineCount * [""])
        #
        # Assemble for sort
        #
        self.headerFrameCsvOut = self.headerFrame.to_csv(index=False, header=False, sep='\t')
        self.detailFrameCsvOut = self.detailFrame.to_csv(index=False, header=False, sep='\t')
        headerLines = self.headerFrameCsvOut.splitlines()
        detailLines = self.detailFrameCsvOut.splitlines()
        combinedLines = headerLines + detailLines
        sortedLines = sorted(combinedLines)

        # Clip off leading transaction identifier:  Not needed in Cougar Mountain
        # Also remove
        clippedSortedLines = []
        for sortedLine in sortedLines:
            new = re.sub(r'[0-9][0-9][0-9]\t[1-2]', '', sortedLine)
            clippedSortedLines.append(new)

        headerColumns = self.headerFrame.columns[1:]
        detailColumns = self.detailFrame.columns[1:]
        headerHeader = "\t".join(headerColumns)
        detailHeader = "\t".join(detailColumns)
        allLines = [headerHeader] + [detailHeader] + clippedSortedLines

        resultCsv = "\n".join(allLines)
        # Remove "sort order" from header and detail indicators (enough times)
        resultCsv = resultCsv.replace("\t1H\t","\tH\t",10000)
        resultCsv = resultCsv.replace("\t2D\t", "\tD\t", 10000)
        print("got here")


        with open(self.tgtDataPath, 'w+') as dst:
            dst.write(resultCsv)

        print('built')


class Transmuter:

    def __init__(self):
        self.templatePath = MASTER_CONVERSION_DIR + TEMPLATES
        self.srcDataPath = MASTER_CONVERSION_DIR + SOURCE

    def transmute(self):

        self.srcFiles = []
        # r=root, d=directories, f = files
        for r, d, f in os.walk(self.srcDataPath):
            for file in f:
                self.srcFiles.append(file)
                print(file)

        ## TODO fix names!!!
        for f in self.srcFiles:
            fileName = str(f)
            conv = None

            if fileName == 'Cougar_Mountain_-_All_Donors_Setup.xls':
                template = AR_CUSTOMER_LIST + ".xls"
                conv = DPCustomerTransmuter(template, fileName)

            if fileName == 'Cougar_Mountain_-_Transaction_Report.xls':
                template = 'SA Transactions.xlsx'
                conv = DPTransactionTransmuter(template, fileName)

            if conv:
                conv.load()
                conv.build()
                print("converted fileName")
            else:
                print('Unknown source file: ' + fileName)

IMPORT_PATH="C:/Users/DELL/Dropbox (Bridges)/NCE Moving to Denali Cougar Mountain/Final imports"
DPO_SA_Activity_Imports="/DPO SA Activity Imports/"
DPO_TRANSACTION_PATH= "DPO Transactions - Apr 24_Apr 30.xls"

###################################################################################
#
AR_CUSTOMER_LIST = "AR Customer List"
AR_CUSTOMER_LIST__DATA_FILE = TARGET_DATA_DIR + AR_CUSTOMER_LIST + ".txt"


class Window(tk.Frame):

    def __init__(self, master=None):
        tk.Frame.__init__(self, master)
        self.master = master
        self.init_window()
        master.geometry("500x400")



    def init_window(self):

        self.master.title("Convert to Cougar Mountain")

        # allowing the widget to take the full space of the root window
        self.pack(fill=tk.BOTH, expand=1)

        quitButton = tk.Button(self, text="Exit",command=self.client_exit)
        runButton = tk.Button(self, text="Run", command=self.client_run)
        selectButton = tk.Button(self, text="Select", command=self.client_select)
        textArea = tk.Text(self.master, height=20, width=60)
        textArea.pack()

        self.srcFiles = []
        # r=root, d=directories, f = files
        for r, d, f in os.walk(MASTER_CONVERSION_DIR + SOURCE):
            for file in f:
                self.srcFiles.append(file)
                textArea.insert(tk.END, file + "\n")

        quitButton.place(x=0, y=0)
        runButton.place(x=30, y=0)
        selectButton.place(x=65,y=0)

        # S = tk.Scrollbar(root)
        # T = tk.Text(root, height=40, width=80)
        # S.pack(side=tk.RIGHT, fill=tk.Y)
        # T.pack(side=tk.LEFT, fill=tk.Y)
        # S.config(command=T.yview)
        # T.config(yscrollcommand=S.set)
        # quote = """HAMLET: To be, or not to be--that is the question:
        # Whether 'tis nobler in the mind to suffer
        # The slings and arrows of outrageous fortune
        # Or to take arms against a sea of troubles
        # And by opposing end them. To die, to sleep--
        # No more--and by a sleep to say we end
        # The heartache, and the thousand natural shocks
        # That flesh is heir to. 'Tis a consummation
        # Devoutly to be wished."""
        # T.insert(tk.END, quote)

    def client_exit(self):
        print("exit!")
        exit()

    def client_run(self):
        print("run!")
        transmuter = Transmuter()
        transmuter.transmute()
        print("run complete!")

    def client_select(self):
        # self.filename = tk.filedialog.askopenfilename(initialdir="/User", title="Select file",
        #                                               filetypes=(("jpeg files", "*.jpg"), ("all files", "*.*")))
        print("select!")
        self.source = tk.filedialog.askdirectory(initialdir="/User", title="Select dir")
        print(self.source)


def main():

    root = tk.Tk()

    app = Window(root)
    root.mainloop()
    print("done all")


if __name__ == '__main__':
    main()
