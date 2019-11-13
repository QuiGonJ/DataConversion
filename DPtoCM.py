#!/usr/bin/python
# Convert CSVs from Donor Perfect to Cougar Mountain
#
# Notes:
#   1. GitHub wiki: https://github.com/QuiGonJ/DataConversion/wiki
#   2. Manual procedure: https://github.com/QuiGonJ/DataConversion/wiki/Cougar-Mountain-Transaction-Export-from-Donor-Perfect-Online(DPO)
#
# TODO:
#   - Add run log recording each conversion
#
import math
import re
import tkinter as tk
from tkinter import filedialog
import pandas as pd
import os

MASTER_CONVERSION_DIR = "C:\\Data\\Documents\\Conversion\\"
SOURCE = "Source\\"
TARGET = "Target\\"
TEMPLATES = "Templates\\"
#
SRC_DATA_DIR=MASTER_CONVERSION_DIR + SOURCE
TARGET_DATA_DIR=MASTER_CONVERSION_DIR + TARGET
TEMPLATES_DATA_DIR=MASTER_CONVERSION_DIR + TEMPLATES

BRIDGES_BANK_ACCOUNT_CODE = "BA5198"

def fileBaseOnly(path): return os.path.basename(path).split('.')[0]


def normalizedName(first, last):
    if len(first) == 0:
        first = last
        last = ""
    return (first + "" + last).strip()

def reformStockCode(glNumber):
    #
    # Per stock code determination as explained by Rick Ridgway 19.7.24
    #
    if glNumber in ACCOUNT_CODE_SET:
        return glNumber

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

class DPCustomerTransmuter:
    """Customers"""
    convCount = 0

    def __init__(self, srcDataFile):
        template = AR_CUSTOMER_LIST + ".xls"
        self.templatePath = MASTER_CONVERSION_DIR + TEMPLATES + template
        self.srcDataPath = MASTER_CONVERSION_DIR + SOURCE + srcDataFile
        self.tgtDataPath = MASTER_CONVERSION_DIR + TARGET + fileBaseOnly(template) + '.txt'


    def load(self):

        self.templateSheet = pd.read_excel(self.templatePath, sheet_name='Sheet1', skiprows=0)
        self.templateCodes = pd.read_excel(self.templatePath, sheet_name='Delete this when done', skiprows=0)
        self.templateColumns = self.templateSheet.columns

        self.dpData = pd.read_excel(self.srcDataPath, sheet_name=0, skiprows=1, skipfooter=0).copy()
        self.dpDataColumns = self.dpData.columns


    def build(self):

        ids = [int(id) for id in self.dpData['Donor ID']]
        dataLineCount = len(ids)
        self.df = pd.DataFrame(index=range(0, len(ids)), columns=self.templateSheet.columns)

        self.df['Customer Number'] = pd.Series(ids)
        self.df['AR Code'] = pd.Series(dataLineCount * ["AR"])
        self.df['Customer Type'] = pd.Series(dataLineCount * [""])
        self.df['Customer Name'] = \
            self.dpData['First Name (FIRST_NAME)'] + " " + self.dpData['Last Name (LAST_NAME)']
        self.df['Customer Name'].str.strip()

        self.df['Billing Contact Name'] = self.dpData['Optional Line']
        self.df['Billing Address Line 1'] = self.dpData['Address'].str.strip()
        self.df['Billing Address Line 2'] = self.dpData['Address 2']

        addr2s = []
        for i in range(len(self.dpData['Address 2'])):
            addr = str(self.dpData['Address 2'][i]).strip()
            if addr in [None, "None", "nan", ""]:
                addr = " "
            addr2s.append(addr)

        self.df['Billing Address Line 2'] = addr2s

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

        dataLines = self.df.to_csv(index=False, sep='\t').split("\n")[1:]
        self.arCustomerListCsvOut = '\n'.join(dataLines)

        with open(self.tgtDataPath, 'w+') as dst:
            dst.write(self.arCustomerListCsvOut)


# These account keys are special case custom mappings
# used for Transaction translation
ACCOUNT_KEYS = {
    '423000000030000':'GRANT',
    '511000000030000': 'ASSESS',
    '518000000030000': 'PSFEES',
    '518000000071100': 'PSNFEE',
    '518000000030000': 'SUPPT',
    '549000000030000': 'FR',
    '581100000030000': 'ACTION',
    '581200000030000': 'SPEDN',
    '581300000030000': 'SPEAD',
    '581400000030000': 'TABLE',
    '581500000030000': 'TICKT',
    '741000000030000': '74100'
}
ACCOUNT_KEY_SET = ACCOUNT_KEYS.keys()
ACCOUNT_CODE_SET = ACCOUNT_KEYS.values()

class DPTransactionTransmuter:
    """Donor Perfect Transactions"""
    convCount = 0

    def __init__(self, srcDataFile):
        transactionTemplate = 'SA Transactions.xls'
        brActivityTemplate = 'BR Activity.xls'

        self.transactionTemplatePath = MASTER_CONVERSION_DIR + TEMPLATES + transactionTemplate
        self.brActivityTemplatePath = MASTER_CONVERSION_DIR + TEMPLATES + brActivityTemplate
        self.srcDataPath = MASTER_CONVERSION_DIR + SOURCE + srcDataFile
        self.tgtTransactionDataPath = MASTER_CONVERSION_DIR + TARGET + fileBaseOnly(transactionTemplate) + '.txt'
        self.tgtBRActivityDataPath = MASTER_CONVERSION_DIR + TARGET + fileBaseOnly(brActivityTemplate) + '.txt'

    def load(self):

        # Transaction templates
        self.transactionHeaderTemplate = pd.read_excel(self.transactionTemplatePath, sheet_name='Sheet1', skiprows=0, nrows=1)
        self.transactionHeaderColumns = self.transactionHeaderTemplate.columns

        self.transactionDetailTemplate = pd.read_excel(self.transactionTemplatePath, sheet_name='Sheet1', skiprows=2, nrows=1)
        self.transactionDetailColumns = self.transactionDetailTemplate.columns

        # Bank reconciliation templates
        self.brActivityHeaderTemplate = pd.read_excel(self.brActivityTemplatePath, sheet_name='Sheet1', skiprows=0, nrows=1)
        self.brActivityHeaderColumns = self.brActivityHeaderTemplate.columns

        self.brActivityDetailTemplate = pd.read_excel(self.brActivityTemplatePath, sheet_name='Sheet1', skiprows=2, nrows=1)
        self.brActivityDetailColumns = self.brActivityDetailTemplate.columns

        self.dpData = pd.read_excel(self.srcDataPath, sheet_name=0, skiprows=1, skipfooter=0).copy()
        self.dpDataColumns = self.dpData.columns
        print("Data loaded: " + self.srcDataPath)

    def build(self):
        self.buildTransactions()
        self.buildBankReconciliation()


    def buildTransactions(self):

        ids = [int(id) for id in self.dpData['Donor ID']]

        headerFrame = pd.DataFrame(index=range(0, len(ids)), columns=self.transactionHeaderColumns)
        detailFrame = pd.DataFrame(index=range(0, len(ids)), columns=self.transactionDetailColumns)
        dataLineCount = len(ids)
        glNumbers = [str(n) for n in self.dpData['General Ledger']]

        # Replace occurances of 7BL with 000 (Ref. R. Ridgway 2019.7.31)
        for i in range(dataLineCount):
            possibleCode = glNumbers[i].replace('7BL','000').strip()
            if possibleCode in ACCOUNT_KEY_SET:
                glNumbers[i] = ACCOUNT_KEYS[possibleCode]

            name = str(headerFrame['Shipping Address Contact'][i]).strip()
            if name in ['', 'nan']:
                name = str((self.dpData['Last Name (LAST_NAME)'][i])).strip()
                headerFrame['Shipping Address Contact'].loc[i] = name

        stockCodes = [reformStockCode(n) for n in glNumbers]
        txnIds = ["{:03d}".format(value) for value in range(dataLineCount)]
        #
        # Header
        #
        headerFrame.insert(0, "Transaction Number", txnIds, True)
        headerFrame['Header Identifier'] = pd.Series(dataLineCount * ["1H"])
        headerFrame['Shipping Customer'] = self.dpData["Donor ID"]
        headerFrame['Shipping Address Contact'] = \
            self.dpData['First Name (FIRST_NAME)'] + " " + self.dpData['Last Name (LAST_NAME)']
        headerFrame['Shipping Address Contact'].str.strip()

        # For organization names (where no first name) use last name only.
        DBGlenBefore = len(headerFrame['Shipping Address Contact'])
        for i in range(dataLineCount):
            name = str(headerFrame['Shipping Address Contact'][i]).strip()
            if name in ['', 'nan']:
                altName = str(self.dpData['Last Name (LAST_NAME)'][i]).strip()
                DBGBefore = len(headerFrame['Shipping Address Contact'])
                headerFrame['Shipping Address Contact'][i] = altName
                DBGafter = len(headerFrame['Shipping Address Contact'])
                if (DBGBefore != DBGafter):
                  print("DBG {} {}", DBGBefore,DBGafter)
                  print("")

        DBGlenAfter = len(headerFrame['Shipping Address Contact'])
        if (DBGlenBefore != DBGlenAfter):
            print("ERROR: frame accidentally extended")

        headerFrame['Shipping Address Line 1'] = pd.Series(dataLineCount * [""])
        headerFrame['Shipping Address Line 2'] = pd.Series(dataLineCount * [""])
        headerFrame['Shipping Address City'] = pd.Series(dataLineCount * [""])
        headerFrame['Shipping Address State/Province'] = pd.Series(dataLineCount * [""])
        headerFrame['Shipping Address Postal Code'] = pd.Series(dataLineCount * [""])
        headerFrame['Shipping Address Counry'] = pd.Series(dataLineCount * [""])
        headerFrame['Cash/Check/CC/Chg'] = pd.Series(dataLineCount * ["0"])
        headerFrame['Transaction Type'] = pd.Series(dataLineCount * ["0"])


        # If check number is missing, use reference number instead.
        checkNumbers = []
        for i in range(dataLineCount):
            strCheckNumber = str(self.dpData['Reference / Check Number'][i])
            if strCheckNumber in ["nan", "", " "]:
                strCheckNumber = str(self.dpData['Reference Number'][i])
                if strCheckNumber in ["nan", "", " "]:
                    strCheckNumber = "Error: Missing Ref Number"
            checkNumbers.append(strCheckNumber)

        headerFrame['Invoice Number'] = checkNumbers
        headerFrame['PO Number'] = pd.Series(dataLineCount * [""])
        headerFrame['Ship Via Code'] = pd.Series(dataLineCount * [""])
        headerFrame['Department Code'] = stockCodes
        headerFrame['Saleperson Code'] = pd.Series(dataLineCount * [""])
        headerFrame['Sales Tax Code'] = pd.Series(dataLineCount * [""])
        headerFrame['Terms Code'] = pd.Series(dataLineCount * [""])
        headerFrame['Discount Code AR'] = pd.Series(dataLineCount * [""])
        headerFrame['Check Number'] = pd.Series(dataLineCount * [""])
        headerFrame['Check authorization'] = pd.Series(dataLineCount * [""])
        headerFrame['Check Account Number'] = pd.Series(dataLineCount * [""])
        headerFrame['Check Routing Number'] = pd.Series(dataLineCount * [""])
        headerFrame["Check Driver's Lic No"] = pd.Series(dataLineCount * [""])
        headerFrame['Credit Card Code'] = pd.Series(dataLineCount * [""])
        headerFrame['Credit Card Authorization'] = pd.Series(dataLineCount * [""])
        headerFrame['Invoice Date'] = self.dpData['Created Date']
        headerFrame['Order Date'] = pd.Series(dataLineCount * [""])
        headerFrame['Shipping Date'] = pd.Series(dataLineCount * [""])
        headerFrame['UDF1'] = pd.Series(dataLineCount * [""])
        headerFrame['UDF2'] = pd.Series(dataLineCount * [""])
        headerFrame['UDF3'] = pd.Series(dataLineCount * [""])
        headerFrame['UDF4'] = pd.Series(dataLineCount * [""])
        headerFrame['UDF5'] = pd.Series(dataLineCount * [""])
        headerFrame['Printed Flag'] = pd.Series(dataLineCount * [""])
        headerFrame['Shipping Phone'] = pd.Series(dataLineCount * [""])
        headerFrame['Shipping Fax'] = pd.Series(dataLineCount * [""])
        headerFrame['Payer'] = pd.Series(dataLineCount * [""])
        #
        # Detail
        #
        detailFrame.insert(0, "Transaction Number", txnIds, True)
        detailFrame['Detail Identifier'] = pd.Series(dataLineCount * ["2D"])
        detailFrame['Line Type'] = pd.Series(dataLineCount * ["1"])
        detailFrame['Stock/Code'] = stockCodes
        detailFrame['Stock Location'] = pd.Series(dataLineCount * [""])
        detailFrame['Description'] = self.dpData['General Ledger Descr']
        for i in range(dataLineCount):
            descr = str(detailFrame['Description'][i])
            if descr == "nan":
                alt = str(detailFrame['Stock/Code'][i])
                detailFrame['Description'][i] = alt.strip()

        detailFrame['Sales Dept Code'] = pd.Series(dataLineCount * [""])
        detailFrame['Salesperson Code'] = pd.Series(dataLineCount * [""])
        detailFrame['Sales Tax Code'] = pd.Series(dataLineCount * [""])
        detailFrame['Comment Code'] = pd.Series(dataLineCount * [""])
        detailFrame['Taxable'] = pd.Series(dataLineCount * ["0"])
        detailFrame['Promotion Code'] = pd.Series(dataLineCount * [""])
        detailFrame['Discount Code'] = pd.Series(dataLineCount * [""])
        detailFrame['Discount%'] = pd.Series(dataLineCount * [""])
        detailFrame['Quantity Ordered'] = pd.Series(dataLineCount * ["1"])
        detailFrame['Quantity Shipped'] = pd.Series(dataLineCount * ["1"])
        detailFrame['Quantity Backordered'] = pd.Series(dataLineCount * [""])
        # Unit price is Gift Amount but without dollar sign.
        for i in range(dataLineCount):
            unitPrice = str(self.dpData['Gift Amount'][i])
            detailFrame['Unit Price'][i] = unitPrice.replace('$', '', 1).replace(',', '', 1)

        detailFrame['Promotional Price'] = pd.Series(dataLineCount * [""])
        detailFrame['Serial Number'] = pd.Series(dataLineCount * [""])
        detailFrame['UDF1'] = pd.Series(dataLineCount * [""])
        detailFrame['UDF2'] = pd.Series(dataLineCount * [""])
        detailFrame['UDF3'] = pd.Series(dataLineCount * [""])
        detailFrame['UDF4'] = pd.Series(dataLineCount * [""])
        detailFrame['UDF5'] = pd.Series(dataLineCount * [""])
        detailFrame['Misc Price'] = pd.Series(dataLineCount * [""])
        detailFrame['For Lease'] = pd.Series(dataLineCount * [""])
        detailFrame['Term Start Date'] = pd.Series(dataLineCount * [""])
        detailFrame['Term Expiration Date'] = pd.Series(dataLineCount * [""])
        #
        # Assemble for sort
        #
        headerFrameCsvOut = headerFrame.to_csv(index=False, header=False, sep='\t')
        detailFrameCsvOut = detailFrame.to_csv(index=False, header=False, sep='\t')
        headerLines = headerFrameCsvOut.splitlines()
        detailLines = detailFrameCsvOut.splitlines()
        combinedLines = headerLines + detailLines
        sortedLines = sorted(combinedLines)

        # Clip off leading transaction identifier:  Not needed in Cougar Mountain
        clippedSortedLines = []
        for sortedLine in sortedLines:
            new = re.sub(r'[0-9][0-9][0-9]\t[1-2]', '', sortedLine)
            clippedSortedLines.append(new)

        resultCsv = "\n".join(clippedSortedLines)
        # Remove "sort order" from header and detail indicators (enough times)
        resultCsv = resultCsv.replace("\t1H\t","\tH\t",10000)
        resultCsv = resultCsv.replace("\t2D\t", "\tD\t", 10000)

        with open(self.tgtTransactionDataPath, 'w+') as dst:
            dst.write(resultCsv)

    def buildBankReconciliation(self):

        ids = [int(id) for id in self.dpData['Donor ID']]

        headerFrame = pd.DataFrame(index=range(0, len(ids)), columns=self.brActivityHeaderColumns)
        detailFrame = pd.DataFrame(index=range(0, len(ids)), columns=self.brActivityDetailColumns)
        dataLineCount = len(ids)
        glNumbers = [str(n) for n in self.dpData['General Ledger']]
        # Replace occurances of 7BL with 000 (Ref. R. Ridgway 2019.7.31)
        for i in range(dataLineCount):
            glNumbers[i] = glNumbers[i].replace('7BL','000')

        txnIds = ["'{:03d}'".format(value) for value in range(dataLineCount)]
        #
        # Header
        #
        headerFrame.insert(0, "Transaction Number", txnIds, True) # Add column
        headerFrame['Transaction Number'] = list(range(len(ids)))
        headerFrame['Header Identifier'] = pd.Series(dataLineCount * ["1H"])
        headerFrame['Bank Account Code'] = pd.Series(dataLineCount * [BRIDGES_BANK_ACCOUNT_CODE])
        headerFrame['Check/Doc Number'] = self.dpData['Reference / Check Number']
        headerFrame['Payee Description'] = pd.Series(dataLineCount * ["Donation"])
        headerFrame['Memo Description'] = self.dpData["General Ledger Descr"]
        for i in range(dataLineCount):
            headerFrame['Memo Description'].loc[i] = str(headerFrame['Memo Description'][i])[0:35] # Shorten to 35 chars
        headerFrame['Payee Address 1'] = pd.Series(dataLineCount * [""])
        headerFrame['Payee Address 2'] = pd.Series(dataLineCount * [""])
        headerFrame['Payee City'] = pd.Series(dataLineCount * [""])
        headerFrame['Payee State'] = pd.Series(dataLineCount * [""])
        headerFrame['Payee Zip Code'] = pd.Series(dataLineCount * [""])
        headerFrame['Payee Country'] = pd.Series(dataLineCount * ["United States"])
        headerFrame['Bank Account Transfer To'] = pd.Series(dataLineCount * [""])
        headerFrame['Activity Type'] = pd.Series(dataLineCount * ["1"])
        headerFrame['Category Type'] = pd.Series(dataLineCount * [""])
        headerFrame['Check Printed?'] = pd.Series(dataLineCount * [""])
        headerFrame['Activity Date'] = self.dpData['Gift Date']

        moneyAmounts = []
        for i in range(dataLineCount):
            amount = self.dpData['Gift Amount'][i]
            # Remove leading dollar sign and commas
            moneyAmounts.append(amount.replace('$', '').replace(',',''))

        headerFrame['Activity Amount'] = moneyAmounts
        #
        # Detail
        #
        detailFrame.insert(0, "Transaction Number", txnIds, True)
        headerFrame['Transaction Number'] = detailFrame['Transaction Number']
        detailFrame['Detail Identifier'] = pd.Series(dataLineCount * ["2D"])
        detailFrame['Line Description'] = self.dpData['Reference / Check Number']
        # If check number is missing, use reference number instead.
        for i in range(dataLineCount):
            fn = self.dpData['First Name (FIRST_NAME)'][i]
            ln = self.dpData['Last Name (LAST_NAME)'][i]
            if 'nan' == str(fn).lower():
                fn = ''
            if 'nan' == str(ln).lower():
                ln = ''
            description = "Donation - {} {}".format(fn, ln)
            shortenedDescription = description[0:35]
            detailFrame['Line Description'][i] = shortenedDescription.strip() # Column max width

        for i in range(dataLineCount):
            possibleCode = str(glNumbers[i]).strip()
            if possibleCode in ACCOUNT_KEYS.keys():
                acctNumber = ACCOUNT_KEYS[possibleCode]
            else:
                glSuffix = str(glNumbers[i])[-5:]
                acctNumber = "1499000000" + glSuffix
            detailFrame['GL Expense Acct'][i] = acctNumber

        detailFrame['Inv/Doc Number'] = pd.Series(dataLineCount * [""])
        detailFrame['Detail Amount'] = moneyAmounts
        detailFrame['Cash Deposit'] = pd.Series(dataLineCount * [""])
        #
        # Assemble for sort
        #
        headerFrameCsvOut = headerFrame.to_csv(index=False, header=False, sep='\t')
        detailFrameCsvOut = detailFrame.to_csv(index=False, header=False, sep='\t')
        headerLines = headerFrameCsvOut.splitlines()
        detailLines = detailFrameCsvOut.splitlines()
        combinedLines = headerLines + detailLines
        sortedLines = sorted(combinedLines)

        # Clip off leading transaction identifier:  Not needed in Cougar Mountain
        clippedSortedLines = []
        for sortedLine in sortedLines:
            lineRemovedPrefix = re.sub(r'\'[0-9][0-9][0-9]\'\t[1-2]', '', sortedLine)
            clippedSortedLines.append(lineRemovedPrefix)

        resultCsv = "\n".join(clippedSortedLines)
        # Remove "sort order" from header and detail indicators (enough times)
        resultCsv = resultCsv.replace("\t1H\t","\tH\t",10000)
        resultCsv = resultCsv.replace("\t2D\t", "\tD\t", 10000)

        with open(self.tgtBRActivityDataPath, 'w+') as dst:
            dst.write(resultCsv)


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

        for f in self.srcFiles:
            fileName = str(f)
            conv = None

            if fileName == 'Cougar_Mountain_-_All_Donors_Setup.xls':
                conv = DPCustomerTransmuter(fileName)

            if fileName == 'Cougar_Mountain_-_Transaction_Report.xls':
                conv = DPTransactionTransmuter(fileName)

            if conv:
                conv.load()
                conv.build()
                print('converted fileName' + fileName)
            else:
                print('Unknown source file: ' + fileName)

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

    def client_exit(self):
        print("exit!")
        exit()

    def client_run(self):
        print("run!")
        transmuter = Transmuter()
        transmuter.transmute()
        print("run complete!")

    def client_select(self):
        self.source = tk.filedialog.askdirectory(initialdir="/User", title="Select dir")
        print(self.source)

def main():
    root = tk.Tk()
    app = Window(root)
    root.mainloop()
    print("done all")

if __name__ == '__main__':
    main()
