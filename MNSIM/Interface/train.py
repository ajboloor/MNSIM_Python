#-*-coding:utf-8-*-
import torch
import torch.nn as nn
import torch.optim as optim
import torch.optim.lr_scheduler as lr_scheduler
import time
from tensorboardX import SummaryWriter
tensorboard_writer = None

MOMENTUM = 0.9
WEIGHT_DECAY = 0.0005
GAMMA = 0.1
lr = 0.01
MILESTONES = [30, 60]
EPOCHS = 90

TRAIN_PARAMETER = '''\
# TRAIN_PARAMETER
## loss
CrossEntropyLoss
## optimizer
SGD: base_lr %f momentum %f weight_decay %f
## lr_policy
MultiStepLR: milestones [%s] gamma %f epochs %d
'''%(
lr,
MOMENTUM,
WEIGHT_DECAY,
','.join([str(v) for v in MILESTONES]),
GAMMA,
EPOCHS,
)

def train_net(net, train_loader, test_loader, device, prefix):
    global tensorboard_writer
    tensorboard_writer = SummaryWriter(logdir = './MNSIM/Interface/runs/', comment = prefix)
    # set net on gpu
    net.to(device)
    # loss and optimizer
    criterion = nn.CrossEntropyLoss()
    # 用来将scale的学习率和weight_decay均置为0
    standard_params = []
    individu_params = []
    for param in net.parameters():
        if (param.size() == torch.Size([1])):
            individu_params.append(param)
        else:
            standard_params.append(param)
    optimizer = optim.SGD([
                           {'params': individu_params, 'lr': 0., 'weight_decay': 0.},
                           {'params': standard_params, 'lr': lr, 'weight_decay': WEIGHT_DECAY},
                           ], momentum = MOMENTUM)
    # optimizer = optim.SGD(net.parameters(), lr = lr, weight_decay = WEIGHT_DECAY, momentum = MOMENTUM)
    scheduler = lr_scheduler.MultiStepLR(optimizer, milestones = MILESTONES, gamma = GAMMA)
    # epochs
    for epoch in range(EPOCHS):
        # train
        net.train()
        scheduler.step()
        for i, (images, labels) in enumerate(train_loader):
            net.zero_grad()
            images = images.to(device)
            labels = labels.to(device)
            outputs = net(images)
            loss = criterion(outputs, labels)
            loss.backward()
            optimizer.step()
            print(f'epoch {epoch+1:3d}, {i:3d}|{len(train_loader):3d}, loss: {loss.item():2.4f}', end = '\r')
            tensorboard_writer.add_scalars('train_loss', {'train_loss': loss.item()}, epoch * len(train_loader) + i)
        eval_net(net, test_loader, epoch + 1, device)
        torch.save(net.state_dict(), f'./MNSIM/Interface/zoo/{prefix}_params.pth')

# show_sche 是一个模式， 0 代表正常训练，不显示进度，记录
# 1 代表RRAM测试，显示进度，不记录
# 2 代表单纯测试，不显示进度，不记录

def eval_net(net, test_loader, epoch, device):
    # set net on gpu
    net.to(device)
    net.eval()
    test_correct = 0
    test_total = 0
    with torch.no_grad():
        for i, (images, labels) in enumerate(test_loader):
            images = images.to(device)
            test_total += labels.size(0)
            outputs = net(images)
            # predicted
            labels = labels.to(device)
            _, predicted = torch.max(outputs, 1)
            test_correct += (predicted == labels).sum().item()
    print('%s After epoch %d, accuracy is %2.4f' % \
          (time.asctime(time.localtime(time.time())), epoch, test_correct / test_total))
    if tensorboard_writer != None:
        tensorboard_writer.add_scalars('test_acc', {'test_acc': test_correct / test_total}, epoch)
    return test_correct / test_total

if __name__ == '__main__':
    print(TRAIN_PARAMETER)