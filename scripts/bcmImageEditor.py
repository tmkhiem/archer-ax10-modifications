#!/usr/bin/env python3

# Broadcom Image Editor by BigNerd95

import sys, os, struct, Broadcom
from argparse import ArgumentParser, FileType

def get_data(input_file, start, length):
    input_file.seek(start, 0)
    return input_file.read(length)

def create_write_file(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(data)

##################
# main functions #
##################

def merge(input_file, rootfs_file, kernel_file, output_file, signature2=None):
    print("** Broadcom Image merge **")
    header = get_data(input_file, 0, Broadcom.TAG_LEN)
    tag = Broadcom.Tag(header)
    print("Original firmware")
    print(tag)
    print()

    print("Merging image...\n")
    original_cfe  = get_data(input_file, Broadcom.TAG_LEN, tag.cfeLen) # may be empty       
    dtb_data = get_data(input_file, Broadcom.TAG_LEN + tag.cfeLen + tag.rootfsLen + tag.kernelLen, 0x1410)
    
    input_file.seek(0,2)
    postfixlen = input_file.tell() - (Broadcom.TAG_LEN + tag.cfeLen + tag.rootfsLen + tag.kernelLen + 0x1410)    
    postfix_data = get_data(input_file, Broadcom.TAG_LEN + tag.cfeLen + tag.rootfsLen + tag.kernelLen + 0x1410, postfixlen)
    
    custom_rootfs = rootfs_file.read()
    custom_kernel = kernel_file.read()
    newImage = original_cfe + custom_rootfs + custom_kernel + dtb_data

    # update header fields
    tag.signature2 = signature2 if signature2 else tag.signature2
    tag.imageLen   = len(newImage)
    tag.rootfsLen  = len(custom_rootfs)
    tag.kernelAddr = tag.rootfsAddr + len(custom_rootfs)
    tag.kernelLen  = len(custom_kernel)
    tag.imageCRC   = Broadcom.jamCRC(newImage)
    tag.rootfsCRC  = Broadcom.jamCRC(custom_rootfs)
    tag.kernelCRC  = Broadcom.jamCRC(custom_kernel)
    #tag.dtbCRC     = Broadcom.jamCRC(dtb_data)
    tag.updateTagCRC()

    print("Custom firmware")
    print(tag)

    output_file.write(tag.__toBin__())
    
    newImage = newImage + postfix_data
    output_file.write(newImage)

    input_file.close()
    rootfs_file.close()
    kernel_file.close()
    output_file.close()    

def split(input_file, directory):
    print("** Broadcom Image split **")
    header = get_data(input_file, 0, Broadcom.TAG_LEN)
    tag = Broadcom.Tag(header)

    path = os.path.join(directory, '')
    if os.path.exists(path):
        print("Directory", os.path.basename(path) , "already exists, cannot split!")
        return

    #cfe    = get_data(input_file, Broadcom.TAG_LEN, tag.cfeLen)
    rootFS = get_data(input_file, Broadcom.TAG_LEN + tag.cfeLen, tag.rootfsLen)
    kernel = get_data(input_file, Broadcom.TAG_LEN + tag.cfeLen + tag.rootfsLen, tag.kernelLen)
    
    input_file.seek(0,2)
    postfixlen = input_file.tell() - (Broadcom.TAG_LEN + tag.cfeLen + tag.rootfsLen + tag.kernelLen)
    print('File size: ', input_file.tell())
    print('-------------------')
    print('Tag length: ', Broadcom.TAG_LEN)
    print('CFE length: ', tag.cfeLen)        
    print('RootFS size: ', len(rootFS))
    print('Kernel size: ', len(kernel))
    print('Postfix length: ', postfixlen)
    print('Total = ',Broadcom.TAG_LEN + tag.cfeLen + tag.rootfsLen + tag.kernelLen+postfixlen)
    
    postfix = get_data(input_file, Broadcom.TAG_LEN + tag.cfeLen + tag.rootfsLen + tag.kernelLen, postfixlen)

    #create_write_file(path + 'cfe', cfe)
    create_write_file(path + 'rootfs', rootFS)
    create_write_file(path + 'kernel', kernel)
    create_write_file(path + 'post', postfix)

    input_file.close()


def info(input_file):
    print("** Broadcom Image info **")
    header = get_data(input_file, 0, Broadcom.TAG_LEN)
    tag = Broadcom.Tag(header)
    print(tag)
    input_file.close()

def parse_cli():
    parser = ArgumentParser(description='** Broadcom Image Editor by BigNerd95 **')
    subparser = parser.add_subparsers(dest='subparser_name')

    infoParser = subparser.add_parser('info', help='Print Tag (header) info')
    infoParser.add_argument('-i', '--input', required=True, metavar='INPUT_FILE', type=FileType('rb'))

    splitParser = subparser.add_parser('split', help='Extract rootfs and kernel from image')
    splitParser.add_argument('-i', '--input', required=True, metavar='INPUT_FILE', type=FileType('rb'))
    splitParser.add_argument('-d', '--directory', required=True, metavar='EXTRACT_DIRECTORY')

    mergeParser = subparser.add_parser('merge', help='Create a new image with custom rootfs and kernel using the original image as base')
    mergeParser.add_argument('-i', '--input',  required=True, metavar='INPUT_FILE', type=FileType('rb'))
    mergeParser.add_argument('-r', '--rootfs', required=True, metavar='ROOTFS_FILE', type=FileType('rb'))
    mergeParser.add_argument('-k', '--kernel', required=True, metavar='KERNEL_FILE', type=FileType('rb'))
    mergeParser.add_argument('-o', '--output', required=True, metavar='OUTPUT_FILE', type=FileType('wb'))    
    mergeParser.add_argument('-s', '--signature',     required=False, metavar='SIGNATURE_2', type=str)

    if len(sys.argv) < 2:
        parser.print_help()

    return parser.parse_args()

def main():
    args = parse_cli()
    if args.subparser_name == 'info':
        info(args.input)
    elif args.subparser_name == 'split':
        split(args.input, args.directory)
    elif args.subparser_name == 'merge':
        merge(args.input, args.rootfs, args.kernel, args.output, args.signature)

if __name__ == '__main__':
    main()
